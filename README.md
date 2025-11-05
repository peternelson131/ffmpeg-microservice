# FFmpeg Video Processing Microservice

A lightweight Flask-based microservice that extracts audio and video streams from video files using FFmpeg. Designed to run on Railway.app's free tier and integrate seamlessly with n8n Cloud workflows.

## Features

- Extract audio from video as MP3
- Extract video without audio as MP4
- Process videos and get both outputs simultaneously
- Support for multiple video formats (MP4, AVI, MOV, MKV, WebM, FLV)
- RESTful API endpoints
- Docker containerized
- Health check endpoint
- Free hosting on Railway.app

## Use Case

This microservice bridges the gap between n8n Cloud (which cannot run FFmpeg) and video processing workflows:

1. **ElevenLabs** generates dubbed audio
2. **n8n** merges audio with original video
3. **This service** extracts audio and video separately
4. **Sync Labs API** performs lip-sync using the extracted files

## API Endpoints

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "ffmpeg_available": true,
  "version": "1.0.0"
}
```

### Process Video (Extract Both Audio and Video)

```bash
POST /process-inline
Content-Type: multipart/form-data

video: <video_file>
```

Returns a ZIP file containing:
- `{job_id}_audio.mp3` - Extracted audio
- `{job_id}_video.mp4` - Video without audio

Example with curl:
```bash
curl -X POST https://your-app.railway.app/process-inline \
  -F "video=@input.mp4" \
  -o processed.zip
```

### Extract Audio Only

```bash
POST /extract-audio
Content-Type: multipart/form-data

video: <video_file>
```

Returns: MP3 audio file

Example:
```bash
curl -X POST https://your-app.railway.app/extract-audio \
  -F "video=@input.mp4" \
  -o audio.mp3
```

### Extract Video Only (No Audio)

```bash
POST /extract-video
Content-Type: multipart/form-data

video: <video_file>
```

Returns: MP4 video file without audio

Example:
```bash
curl -X POST https://your-app.railway.app/extract-video \
  -F "video=@input.mp4" \
  -o video_no_audio.mp4
```

### Process Video (JSON Response)

```bash
POST /process
Content-Type: multipart/form-data

video: <video_file>
```

Returns JSON with download URLs:
```json
{
  "success": true,
  "job_id": "uuid-here",
  "audio": {
    "filename": "uuid_audio.mp3",
    "size": 1234567,
    "download_url": "/download/uuid/audio"
  },
  "video": {
    "filename": "uuid_video.mp4",
    "size": 9876543,
    "download_url": "/download/uuid/video"
  }
}
```

## Deployment to Railway.app

### Prerequisites

- GitHub account
- Railway.app account (free tier available)

### Step 1: Push to GitHub

```bash
cd ffmpeg-microservice
git init
git add .
git commit -m "Initial commit: FFmpeg microservice"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ffmpeg-microservice.git
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to [Railway.app](https://railway.app/)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `ffmpeg-microservice` repository
5. Railway will automatically:
   - Detect the Dockerfile
   - Build the container
   - Deploy the service
6. Once deployed, Railway will provide a public URL like: `https://your-app.railway.app`

### Step 3: Configure (Optional)

Railway automatically sets the `PORT` environment variable. No additional configuration needed for basic usage.

### Step 4: Test Deployment

```bash
# Health check
curl https://your-app.railway.app/health

# Test audio extraction
curl -X POST https://your-app.railway.app/extract-audio \
  -F "video=@test.mp4" \
  -o output_audio.mp3
```

## Local Development

### Prerequisites

- Python 3.11+
- FFmpeg installed locally

#### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Test locally
curl http://localhost:8080/health
```

### Test with Docker

```bash
# Build image
docker build -t ffmpeg-microservice .

# Run container
docker run -p 8080:8080 ffmpeg-microservice

# Test
curl http://localhost:8080/health
```

## Integration with n8n

### HTTP Request Node Configuration

**Extract Audio Only:**
- Method: `POST`
- URL: `https://your-app.railway.app/extract-audio`
- Body Content Type: `Form-Data`
- Body Parameters:
  - Name: `video`
  - Parameter Type: `File`
  - Input Data Field Name: `data` (or your video binary field)

**Extract Both (ZIP):**
- Method: `POST`
- URL: `https://your-app.railway.app/process-inline`
- Body Content Type: `Form-Data`
- Response Format: `File`
- Body Parameters:
  - Name: `video`
  - Parameter Type: `File`

**Extract Video Only:**
- Method: `POST`
- URL: `https://your-app.railway.app/extract-video`
- Body Content Type: `Form-Data`
- Response Format: `File`

### Example n8n Workflow

```
1. [Webhook/Trigger] → Receive video
2. [HTTP Request] → POST to /extract-audio (get MP3)
3. [HTTP Request] → POST to /extract-video (get MP4)
4. [Process] → Use extracted files in Sync Labs API
5. [Output] → Return processed video
```

## Configuration

### Environment Variables

- `PORT` - Server port (default: 8080, automatically set by Railway)
- `MAX_CONTENT_LENGTH` - Max upload size (default: 500MB)

### File Size Limits

- Maximum upload: 500MB
- Timeout per operation: 5 minutes

### Supported Formats

**Input:** MP4, AVI, MOV, MKV, WebM, FLV
**Output Audio:** MP3 (192kbps, 44.1kHz)
**Output Video:** MP4 (original codec, no re-encoding)

## Monitoring

### Check Service Health

```bash
curl https://your-app.railway.app/health
```

### Railway Dashboard

- View logs in Railway dashboard
- Monitor CPU/memory usage
- Check deployment status

## Troubleshooting

### "File too large" error

Increase `MAX_CONTENT_LENGTH` in `app.py` or split video into smaller segments.

### "Processing timed out"

Increase timeout values in `extract_audio()` and `extract_video_no_audio()` functions.

### FFmpeg errors

Check Railway logs for detailed FFmpeg output. Common issues:
- Corrupted video file
- Unsupported codec
- Insufficient memory

### n8n Integration Issues

- Ensure `Content-Type` is `multipart/form-data`
- Set Parameter Type to `File` (not `String`)
- Check that video binary data is properly passed

## Cost Optimization

Railway.app free tier includes:
- 500 hours/month execution time
- 500MB RAM
- Shared CPU

For production use with high volume, consider:
- Upgrading to Railway Pro ($5/month)
- Using AWS Lambda with FFmpeg layer
- Self-hosting on VPS

## Security Notes

- No authentication implemented (add API keys for production)
- Temporary files are automatically cleaned up
- No persistent storage (files are processed in memory/temp)
- Rate limiting not implemented (consider adding for production)

## Future Enhancements

- [ ] Add API key authentication
- [ ] Support custom audio/video encoding parameters
- [ ] Add video thumbnail generation
- [ ] Implement job queue for large files
- [ ] Add webhook callbacks for async processing
- [ ] Support cloud storage (S3, GCS) for large files
- [ ] Add video format conversion

## License

MIT License - Free to use and modify

## Support

For issues or questions:
1. Check Railway logs
2. Test locally with Docker
3. Verify FFmpeg is working: `curl https://your-app.railway.app/health`

## Author

Built for n8n Cloud + ElevenLabs + Sync Labs video processing workflow.
