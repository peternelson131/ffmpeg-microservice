# Quick Start Guide

Get your FFmpeg microservice running in under 5 minutes!

## Option 1: Deploy to Railway (Fastest - No Local Setup)

### 1. Push to GitHub

```bash
cd ffmpeg-microservice
git init
git add .
git commit -m "Initial commit"
git branch -M main
# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/ffmpeg-microservice.git
git push -u origin main
```

### 2. Deploy on Railway

1. Go to https://railway.app/
2. Sign up/login with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose `ffmpeg-microservice`
6. Wait 2-3 minutes for build & deploy
7. Click on your service → **"Settings"** → **"Generate Domain"**
8. Copy your URL: `https://ffmpeg-microservice-production.up.railway.app`

### 3. Test It

```bash
# Health check
curl https://YOUR-APP.railway.app/health

# Extract audio from a video
curl -X POST https://YOUR-APP.railway.app/extract-audio \
  -F "video=@your-video.mp4" \
  -o audio.mp3
```

**Done!** Your service is live and ready to use with n8n.

---

## Option 2: Run Locally with Docker

### 1. Prerequisites

- Docker installed
- A test video file

### 2. Build & Run

```bash
cd ffmpeg-microservice

# Build Docker image
docker build -t ffmpeg-microservice .

# Run container
docker run -p 8080:8080 ffmpeg-microservice
```

### 3. Test

```bash
# Health check
curl http://localhost:8080/health

# Test audio extraction
curl -X POST http://localhost:8080/extract-audio \
  -F "video=@test.mp4" \
  -o audio.mp3
```

**Or use the test script:**

```bash
./test_service.sh http://localhost:8080 your-video.mp4
```

---

## Option 3: Run Locally with Python (Development)

### 1. Prerequisites

```bash
# macOS
brew install ffmpeg python3

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ffmpeg python3 python3-pip
```

### 2. Install & Run

```bash
cd ffmpeg-microservice

# Install dependencies
pip3 install -r requirements.txt

# Run the service
python3 app.py
```

### 3. Test

```bash
curl http://localhost:8080/health
```

---

## Using with n8n Cloud

### HTTP Request Node Setup

1. Add **HTTP Request** node
2. Configure:
   - **Method:** `POST`
   - **URL:** `https://YOUR-APP.railway.app/extract-audio`
   - **Body Content Type:** `Form-Data`
   - **Specify Body:** `Using Fields Below`
3. Add parameter:
   - **Name:** `video`
   - **Parameter Type:** `File`
   - **Input Data Field Name:** `data` (your video binary field)
4. **Response Format:** `File`

### Example Workflow

```
[Trigger] → [Your Video Source] → [HTTP Request to FFmpeg Service] → [Sync Labs API]
```

---

## Troubleshooting

### Service not responding?

```bash
# Check if container is running
docker ps

# View logs
docker logs <container_id>
```

### FFmpeg not found?

```bash
# Test FFmpeg in container
docker exec <container_id> ffmpeg -version
```

### Railway deployment failed?

1. Check build logs in Railway dashboard
2. Ensure Dockerfile is in root directory
3. Verify requirements.txt is present

---

## Next Steps

- ✅ Service is running
- ✅ Tested with curl
- ⬜ Integrate with n8n
- ⬜ Test with ElevenLabs → FFmpeg → Sync Labs workflow
- ⬜ Add API authentication (see README.md)

## Support

Full documentation: See `README.md`

Quick tests: Run `./test_service.sh`

Need help? Check Railway logs or test locally first!
