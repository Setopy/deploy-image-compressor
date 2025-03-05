from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from PIL import Image
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Test route
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

class ImageCompressor:
    def __init__(self, quality=95, max_size=3840):
        self.quality = quality
        self.max_size = max_size
        self.format_options = {
            'PNG': {
                'optimize': True,
                'compress_level': 6
            },
            'JPEG': {
                'optimize': True,
                'progressive': True,
                'subsampling': '4:4:4'
            }
        }
        
    def calculate_new_dimensions(self, width, height):
        if width <= self.max_size and height <= self.max_size:
            return width, height

        ratio = min(self.max_size / width, self.max_size / height)
        new_width = round(width * ratio)
        new_height = round(height * ratio)
        
        # Ensure dimensions are even numbers for better compression
        new_width = new_width + (new_width % 2)
        new_height = new_height + (new_height % 2)
        
        return new_width, new_height

    def compress_image(self, image_file):
        try:
            logger.info("Starting image compression")
            img = Image.open(image_file)
            logger.info(f"Image opened. Size: {img.size}, Mode:{img.mode}, Format: {img.format}")
            
            if img.mode == 'RGBA':
                logger.info("Converting RGBA to RGB")
                background = Image.new('RGB', img.size, (255, 255, 255))
                img = Image.alpha_composite(background.convert('RGBA'), 
img)
                img = img.convert('RGB')

            width, height = img.size
            new_width, new_height = self.calculate_new_dimensions(width, 
height)
            logger.info(f"New dimensions: {new_width}x{new_height}")
            
            if new_width != width or new_height != height:
                img = img.resize((new_width, new_height), 
Image.Resampling.LANCZOS)

            output_buffer = io.BytesIO()
            format_name = img.format or 'JPEG'
            format_options = self.format_options.get(format_name, 
{}).copy()

            if format_name == 'JPEG':
                format_options['quality'] = self.quality
                format_options['subsampling'] = '4:4:4'
            
            logger.info(f"Saving with format {format_name} and options {format_options}")
            img.save(output_buffer, format=format_name, **format_options)
            output_buffer.seek(0)
            
            buffer_size = output_buffer.getbuffer().nbytes
            logger.info(f"Compressed image size: {buffer_size} bytes")
            
            return output_buffer, format_name.lower()

        except Exception as e:
            logger.error(f"Error in compress_image: {str(e)}")
            raise

@app.route('/compress', methods=['POST'])
def compress_image():
    try:
        if 'file' not in request.files:
            logger.error("No file in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename:
            logger.error("No filename")
            return jsonify({'error': 'No selected file'}), 400
        
        logger.info(f"Processing file: {file.filename}")
        
        quality = int(request.form.get('quality', 95))
        max_size = int(request.form.get('maxSize', 3840))
        
        logger.info(f"Quality: {quality}, Max size: {max_size}")
        
        compressor = ImageCompressor(quality=quality, max_size=max_size)
        output_buffer, format_name = compressor.compress_image(file)
        
        logger.info(f"Compression complete. Format: {format_name}")
        
        return send_file(
            output_buffer,
            mimetype=f'image/{format_name}',
            as_attachment=True,
            download_name=f'compressed_{file.filename}'
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, port=port)
