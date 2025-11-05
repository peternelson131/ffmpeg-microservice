# Simplified FFmpeg + Sync Labs Workflow (No External Storage!)

**Version 2.0 Update:** The FFmpeg microservice now stores files temporarily and returns public URLs directly - no need for file.io, S3, or any external storage!

## What Changed?

**Before (v1.0):**
```
[FFmpeg] → Binary files → [Upload to file.io] → [Sync Labs]
```

**Now (v2.0):**
```
[FFmpeg] → Public URLs (auto-stored for 2 hours) → [Sync Labs]
```

---

## Complete n8n Workflow

### Node 1: "Process with FFmpeg"

**HTTP Request Node:**
- **Method:** `POST`
- **URL:** `https://ffmpeg-microservice-production.up.railway.app/process`
- **Body Content Type:** `Form-Data Multipart`
- **Body Parameters:**
  - Name: `video`
  - Parameter Type: `n8n Binary Data`
  - Input Binary Field: `data` (your ElevenLabs video)
- **Response Format:** `JSON`

**Output:**
```json
{
  "success": true,
  "job_id": "abc-123-def",
  "audio": {
    "url": "https://ffmpeg-microservice-production.up.railway.app/download/abc-123-def/audio",
    "filename": "audio.mp3",
    "size": 1234567
  },
  "video": {
    "url": "https://ffmpeg-microservice-production.up.railway.app/download/abc-123-def/video",
    "filename": "video.mp4",
    "size": 9876543
  },
  "expires_in_hours": 2,
  "message": "Video processed successfully. Files will be available for 2 hours."
}
```

---

### Node 2: "Submit to Sync Labs"

**HTTP Request Node:**

**Authentication:**
- **Header Parameters:**
  - Name: `x-api-key`
  - Value: `YOUR_SYNC_LABS_API_KEY`

**Request:**
- **Method:** `POST`
- **URL:** `https://api.sync.so/v2/generate`
- **Body Content Type:** `JSON`
- **Specify Body:** `Using JSON`

**JSON Body:**
```json
{
  "model": "lipsync-2",
  "input": [
    {
      "type": "video",
      "url": "{{ $json.video.url }}"
    },
    {
      "type": "audio",
      "url": "{{ $json.audio.url }}"
    }
  ]
}
```

**Output:** `{{ $json.id }}` is your Sync Labs job ID

---

### Node 3: "Wait 30 Seconds"

**Wait Node:**
- **Resume:** `After Time Interval`
- **Wait Amount:** `30` seconds

---

### Node 4: "Check Sync Labs Status"

**HTTP Request Node:**

**Authentication:**
- Header: `x-api-key: YOUR_SYNC_LABS_API_KEY`

**Request:**
- **Method:** `GET`
- **URL:** `https://api.sync.so/v2/generate/{{ $('Submit to Sync Labs').item.json.id }}`
- **Response Format:** `JSON`

---

### Node 5: "Is Complete?"

**IF Node:**
- **Condition:** `{{ $json.status }}` **equals** `completed`
- **If No:** Loop back to Node 3 (Wait)
- **If Yes:** Continue to download

---

### Node 6: "Download Final Video"

**HTTP Request Node:**
- **Method:** `GET`
- **URL:** `{{ $('Check Sync Labs Status').item.json.output[0].url }}`
- **Response Format:** `File`

**Output:** Your final lip-synced video! 🎉

---

## Visual Workflow

```
┌─────────────────────────────┐
│ ElevenLabs Dubbed Video     │
│ (Binary MP4)                │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ FFmpeg Microservice         │
│ POST /process               │
│                             │
│ ✓ Extracts audio.mp3        │
│ ✓ Extracts video.mp4        │
│ ✓ Stores for 2 hours        │
│ ✓ Returns public URLs       │
└──────────┬──────────────────┘
           │
           │ Returns:
           │ - audio_url
           │ - video_url
           │
           ▼
┌─────────────────────────────┐
│ Sync Labs API               │
│ POST /v2/generate           │
│                             │
│ Input:                      │
│ - video_url (no audio)      │
│ - audio_url (dubbed)        │
└──────────┬──────────────────┘
           │
           │ Returns: job_id
           │
           ▼
      ┌────────┐
   ┌─►│ Wait   │
   │  │ 30s    │
   │  └───┬────┘
   │      │
   │      ▼
   │  ┌────────────┐
   │  │ Check      │
   │  │ Status     │
   │  └───┬────────┘
   │      │
   │      ▼
   │  ┌─────────────┐
   └──┤ Complete?   │
      └───┬─────────┘
          │ Yes
          ▼
┌─────────────────────────────┐
│ Download Final Video        │
│ (Lip-synced MP4)            │
└─────────────────────────────┘
```

---

## Benefits of v2.0

✅ **No external storage needed** - FFmpeg stores files temporarily
✅ **Handles files >100MB** - No file.io limits
✅ **Simpler workflow** - One less step to configure
✅ **Free** - Uses Railway free tier storage
✅ **Auto-cleanup** - Files deleted after 2 hours
✅ **Direct URLs** - Works perfectly with Sync Labs API

---

## Important Notes

### File Storage

- Files are stored on Railway's server
- **Automatically deleted after 2 hours**
- Storage location: `/tmp/ffmpeg-storage/`
- Each job gets a unique ID

### File Expiry

If you need files longer than 2 hours:
- Change `FILE_EXPIRY_HOURS` in `app.py`
- Redeploy to Railway

### Railway Storage Limits

Railway free tier includes sufficient storage for this workflow. If you process many large videos:
- Upgrade to Railway Pro ($5/month)
- Or add external storage (S3) later

### Large File Support

The microservice now supports files **over 100MB**:
- Up to 500MB per file (configurable)
- Railway handles large file storage
- No external services required

---

## Testing the Workflow

### 1. Test FFmpeg Microservice

```bash
# Health check
curl https://ffmpeg-microservice-production.up.railway.app/health

# Expected output:
{
  "status": "healthy",
  "ffmpeg_available": true,
  "version": "2.0.0",
  "active_jobs": 0,
  "file_expiry_hours": 2
}
```

### 2. Test with a video

```bash
# Process a video
curl -X POST https://ffmpeg-microservice-production.up.railway.app/process \
  -F "video=@test.mp4" \
  | jq

# Expected output:
{
  "success": true,
  "job_id": "abc-123",
  "audio": {
    "url": "https://...../download/abc-123/audio",
    "filename": "audio.mp3",
    "size": 1234567
  },
  "video": {
    "url": "https://...../download/abc-123/video",
    "filename": "video.mp4",
    "size": 9876543
  },
  "expires_in_hours": 2
}
```

### 3. Test download URLs

```bash
# Download audio
curl "https://ffmpeg-microservice-production.up.railway.app/download/abc-123/audio" \
  -o test_audio.mp3

# Download video
curl "https://ffmpeg-microservice-production.up.railway.app/download/abc-123/video" \
  -o test_video.mp4
```

### 4. Verify files play correctly

```bash
# Play audio (macOS)
afplay test_audio.mp3

# Play video (macOS)
open test_video.mp4
```

---

## Troubleshooting

### "Job not found or expired"

**Cause:** Files were already deleted (>2 hours old)

**Solution:** Re-process the video with `/process` endpoint

### "File too large"

**Cause:** Video exceeds 500MB limit

**Solution:**
1. Compress video first
2. Or increase `MAX_CONTENT_LENGTH` in `app.py`

### Sync Labs: "Invalid video URL"

**Cause:** URL not accessible or job expired

**Solution:**
1. Test the URL in a browser first
2. Ensure job is <2 hours old
3. Check Railway logs for errors

### Railway storage full

**Cause:** Too many active jobs

**Solution:**
1. Wait for auto-cleanup (runs every 30 min)
2. Decrease `FILE_EXPIRY_HOURS`
3. Upgrade Railway plan

---

## Cost Analysis

### Free Tier (Railway)

- ✅ 500 hours/month execution time
- ✅ 100GB outbound bandwidth
- ✅ Shared storage
- ✅ Sufficient for testing/low volume

**Cost:** $0

### Production (Railway Pro)

- $5/month base
- $0.000463/GB-hour storage
- $0.10/GB bandwidth

**Example:** 100 videos/day @ 100MB each:
- Storage: ~$0.50/month
- Bandwidth: ~$30/month
- **Total: ~$35.50/month**

### vs. AWS S3 Alternative

- S3: $0.023/GB storage + $0.09/GB bandwidth
- **Similar cost** but adds complexity

**Conclusion:** Railway is cost-effective and simpler!

---

## Next Steps

1. ✅ FFmpeg microservice updated to v2.0
2. ⬜ Deploy to Railway (see below)
3. ⬜ Get Sync Labs API key
4. ⬜ Build n8n workflow
5. ⬜ Test end-to-end

---

## Deployment Instructions

```bash
cd ffmpeg-microservice

# Commit changes
git add .
git commit -m "Update to v2.0: Add URL-based file storage"

# Push to GitHub
git push origin main
```

Railway will automatically:
- Detect the changes
- Rebuild the container
- Deploy the new version

Check deployment at: https://railway.app/dashboard

---

## Environment Variables (Optional)

Set these in Railway if needed:

**BASE_URL** (optional)
- Set to your Railway URL for absolute URLs
- If not set, uses relative URLs (works fine)
- Example: `https://ffmpeg-microservice-production.up.railway.app`

**STORAGE_DIR** (optional)
- Default: `/tmp/ffmpeg-storage`
- Change if you want different location

**FILE_EXPIRY_HOURS** (optional)
- Default: 2 hours
- Change in code and redeploy

---

## Support

For issues:
1. Check Railway logs
2. Test `/health` endpoint
3. Verify Sync Labs API key
4. Check n8n expressions

## Summary

**You now have a complete, self-contained video processing pipeline!**

No external storage required - the FFmpeg microservice handles everything from extraction to temporary hosting, making your Sync Labs integration seamless and cost-effective.
