import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import shutil
from pathlib import Path

app = Flask(__name__)

# Configuration
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_audio(input_path, output_path):
    """Extract audio from video and save as MP3."""
    try:
        command = [
            'ffmpeg',
            '-i', input_path,
            '-vn',  # No video
            '-acodec', 'libmp3lame',  # MP3 codec
            '-ab', '192k',  # Audio bitrate
            '-ar', '44100',  # Sample rate
            '-y',  # Overwrite output file
            output_path
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            raise Exception(f"FFmpeg audio extraction failed: {result.stderr}")

        return True
    except subprocess.TimeoutExpired:
        raise Exception("Audio extraction timed out")
    except Exception as e:
        raise Exception(f"Audio extraction error: {str(e)}")

def extract_video_no_audio(input_path, output_path):
    """Extract video without audio and save as MP4."""
    try:
        command = [
            'ffmpeg',
            '-i', input_path,
            '-an',  # No audio
            '-vcodec', 'copy',  # Copy video codec (faster, no re-encoding)
            '-y',  # Overwrite output file
            output_path
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            raise Exception(f"FFmpeg video extraction failed: {result.stderr}")

        return True
    except subprocess.TimeoutExpired:
        raise Exception("Video extraction timed out")
    except Exception as e:
        raise Exception(f"Video extraction error: {str(e)}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check if FFmpeg is available
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        ffmpeg_available = result.returncode == 0

        return jsonify({
            'status': 'healthy',
            'ffmpeg_available': ffmpeg_available,
            'version': '1.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/process', methods=['POST'])
def process_video():
    """
    Process video: extract audio as MP3 and video without audio as MP4.

    Request:
        - multipart/form-data with 'video' file
        - optional: 'output_format' (json|files) - default: json with URLs

    Response:
        - JSON with base64 encoded files or temporary URLs
        - Or direct file downloads (if output_format=files)
    """

    # Check if video file is present
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']

    if video_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(video_file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    job_id = str(uuid.uuid4())

    try:
        # Save uploaded file
        filename = secure_filename(video_file.filename)
        input_path = os.path.join(temp_dir, f"input_{filename}")
        video_file.save(input_path)

        # Define output paths
        audio_output = os.path.join(temp_dir, f"{job_id}_audio.mp3")
        video_output = os.path.join(temp_dir, f"{job_id}_video.mp4")

        # Extract audio
        extract_audio(input_path, audio_output)

        # Extract video without audio
        extract_video_no_audio(input_path, video_output)

        # Check if files were created successfully
        if not os.path.exists(audio_output):
            raise Exception("Audio file was not created")
        if not os.path.exists(video_output):
            raise Exception("Video file was not created")

        # Get file sizes
        audio_size = os.path.getsize(audio_output)
        video_size = os.path.getsize(video_output)

        # For n8n, we'll return the files as a response
        # n8n can handle file downloads from the response

        return jsonify({
            'success': True,
            'job_id': job_id,
            'audio': {
                'filename': f"{job_id}_audio.mp3",
                'size': audio_size,
                'download_url': f"/download/{job_id}/audio"
            },
            'video': {
                'filename': f"{job_id}_video.mp4",
                'size': video_size,
                'download_url': f"/download/{job_id}/video"
            },
            'message': 'Video processed successfully. Use download URLs to retrieve files.'
        }), 200

    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({
            'error': 'Processing failed',
            'details': str(e)
        }), 500

@app.route('/process-inline', methods=['POST'])
def process_video_inline():
    """
    Process video and return files inline (for direct download).
    Returns a ZIP file containing both audio and video.
    """
    import zipfile

    # Check if video file is present
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']

    if video_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(video_file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    job_id = str(uuid.uuid4())

    try:
        # Save uploaded file
        filename = secure_filename(video_file.filename)
        input_path = os.path.join(temp_dir, f"input_{filename}")
        video_file.save(input_path)

        # Define output paths
        audio_output = os.path.join(temp_dir, f"{job_id}_audio.mp3")
        video_output = os.path.join(temp_dir, f"{job_id}_video.mp4")
        zip_output = os.path.join(temp_dir, f"{job_id}_processed.zip")

        # Extract audio
        extract_audio(input_path, audio_output)

        # Extract video without audio
        extract_video_no_audio(input_path, video_output)

        # Create ZIP file
        with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(audio_output, f"{job_id}_audio.mp3")
            zipf.write(video_output, f"{job_id}_video.mp4")

        # Return ZIP file
        return send_file(
            zip_output,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"processed_{job_id}.zip"
        )

    except Exception as e:
        return jsonify({
            'error': 'Processing failed',
            'details': str(e)
        }), 500
    finally:
        # Clean up after sending file
        # Note: Flask will clean up temp files after response is sent
        pass

@app.route('/extract-audio', methods=['POST'])
def extract_audio_only():
    """Extract only audio from video as MP3."""

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']

    if video_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(video_file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400

    temp_dir = tempfile.mkdtemp()

    try:
        # Save uploaded file
        filename = secure_filename(video_file.filename)
        input_path = os.path.join(temp_dir, f"input_{filename}")
        video_file.save(input_path)

        # Define output path
        audio_output = os.path.join(temp_dir, "audio.mp3")

        # Extract audio
        extract_audio(input_path, audio_output)

        # Return audio file
        return send_file(
            audio_output,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=f"{Path(filename).stem}_audio.mp3"
        )

    except Exception as e:
        return jsonify({
            'error': 'Audio extraction failed',
            'details': str(e)
        }), 500
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/extract-video', methods=['POST'])
def extract_video_only():
    """Extract only video (no audio) from video as MP4."""

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']

    if video_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(video_file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400

    temp_dir = tempfile.mkdtemp()

    try:
        # Save uploaded file
        filename = secure_filename(video_file.filename)
        input_path = os.path.join(temp_dir, f"input_{filename}")
        video_file.save(input_path)

        # Define output path
        video_output = os.path.join(temp_dir, "video.mp4")

        # Extract video without audio
        extract_video_no_audio(input_path, video_output)

        # Return video file
        return send_file(
            video_output,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"{Path(filename).stem}_no_audio.mp4"
        )

    except Exception as e:
        return jsonify({
            'error': 'Video extraction failed',
            'details': str(e)
        }), 500
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({
        'error': 'File too large',
        'max_size': f"{MAX_CONTENT_LENGTH // (1024*1024)}MB"
    }), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors."""
    return jsonify({
        'error': 'Internal server error',
        'details': str(error)
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
