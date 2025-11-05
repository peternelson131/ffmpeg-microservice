import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# Configuration
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
STORAGE_DIR = os.environ.get('STORAGE_DIR', '/tmp/ffmpeg-storage')
BASE_URL = os.environ.get('BASE_URL', '')  # Set in Railway or leave empty for relative URLs
FILE_EXPIRY_HOURS = 2  # Files are kept for 2 hours

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create storage directory
os.makedirs(STORAGE_DIR, exist_ok=True)

# Store job metadata
jobs_metadata = {}

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Remove files older than FILE_EXPIRY_HOURS."""
    while True:
        try:
            current_time = datetime.now()
            for job_id in list(jobs_metadata.keys()):
                job_data = jobs_metadata[job_id]
                created_at = job_data.get('created_at')

                if created_at and (current_time - created_at) > timedelta(hours=FILE_EXPIRY_HOURS):
                    # Remove files
                    job_dir = os.path.join(STORAGE_DIR, job_id)
                    if os.path.exists(job_dir):
                        shutil.rmtree(job_dir, ignore_errors=True)

                    # Remove from metadata
                    del jobs_metadata[job_id]
                    print(f"Cleaned up expired job: {job_id}")

            # Sleep for 30 minutes before next cleanup
            time.sleep(1800)
        except Exception as e:
            print(f"Error during cleanup: {e}")
            time.sleep(1800)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

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

        # Count active jobs
        active_jobs = len(jobs_metadata)

        return jsonify({
            'status': 'healthy',
            'ffmpeg_available': ffmpeg_available,
            'version': '2.0.0',
            'active_jobs': active_jobs,
            'file_expiry_hours': FILE_EXPIRY_HOURS
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
    Returns JSON with public URLs for the extracted files.

    Request:
        - multipart/form-data with 'video' file

    Response:
        - JSON with public URLs for audio and video files
        - Files are stored for 2 hours then automatically deleted
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

        # Create persistent storage directory for this job
        job_dir = os.path.join(STORAGE_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Define output paths in persistent storage
        audio_output = os.path.join(job_dir, "audio.mp3")
        video_output = os.path.join(job_dir, "video.mp4")

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

        # Store job metadata
        jobs_metadata[job_id] = {
            'created_at': datetime.now(),
            'audio_size': audio_size,
            'video_size': video_size,
            'original_filename': filename
        }

        # Build URLs
        base = BASE_URL if BASE_URL else request.host_url.rstrip('/')
        audio_url = f"{base}/download/{job_id}/audio"
        video_url = f"{base}/download/{job_id}/video"

        return jsonify({
            'success': True,
            'job_id': job_id,
            'audio': {
                'url': audio_url,
                'filename': 'audio.mp3',
                'size': audio_size
            },
            'video': {
                'url': video_url,
                'filename': 'video.mp4',
                'size': video_size
            },
            'expires_in_hours': FILE_EXPIRY_HOURS,
            'message': 'Video processed successfully. Files will be available for 2 hours.'
        }), 200

    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        job_dir = os.path.join(STORAGE_DIR, job_id)
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({
            'error': 'Processing failed',
            'details': str(e)
        }), 500
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

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

@app.route('/download/<job_id>/<file_type>', methods=['GET'])
def download_file(job_id, file_type):
    """
    Download extracted audio or video file.

    URL Parameters:
        job_id: The job ID returned from /process
        file_type: Either 'audio' or 'video'
    """

    # Validate file type
    if file_type not in ['audio', 'video']:
        return jsonify({'error': 'Invalid file type. Use "audio" or "video"'}), 400

    # Check if job exists
    if job_id not in jobs_metadata:
        return jsonify({'error': 'Job not found or expired'}), 404

    # Build file path
    job_dir = os.path.join(STORAGE_DIR, job_id)
    if file_type == 'audio':
        file_path = os.path.join(job_dir, 'audio.mp3')
        mimetype = 'audio/mpeg'
        filename = f"{job_id}_audio.mp3"
    else:
        file_path = os.path.join(job_dir, 'video.mp4')
        mimetype = 'video/mp4'
        filename = f"{job_id}_video.mp4"

    # Check if file exists
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    # Return file
    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=False,  # Allow inline viewing
        download_name=filename
    )

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
