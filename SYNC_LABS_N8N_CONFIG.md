# Sync Labs API + n8n Configuration Guide

Complete guide to integrate Sync Labs lip-sync API with n8n Cloud.

## Prerequisites

1. **Sync Labs API Key**
   - Get it from: https://sync.so/settings/api-keys
   - Keep it secure - you'll use it in n8n

2. **Public URLs Required**
   - Sync Labs API requires publicly accessible URLs
   - Does NOT accept direct binary file uploads
   - You need URLs for both video and audio files

---

## API Details

**Endpoint:** `POST https://api.sync.so/v2/generate`

**Authentication:** Header `x-api-key: YOUR_API_KEY`

**Method:** Async (submit job → poll for status → get result)

---

## Workflow Architecture

### Current Challenge

```
[ElevenLabs] → [Video Binary] → [FFmpeg] → [Audio + Video Binary]
                                              ↓
                                        ❌ Sync Labs needs URLs, not binaries!
```

### Solution 1: Upload to Temporary Storage

```
[ElevenLabs] → [Video Binary]
    ↓
[FFmpeg Microservice] → Extract audio.mp3 + video.mp4
    ↓
[Upload to file.io or S3] → Get public URLs
    ↓
[Sync Labs API] → Submit job with URLs
    ↓
[Poll Status] → Check until complete
    ↓
[Download Result] → Final lip-synced video
```

### Solution 2: Use URLs Throughout (If Available)

```
[ElevenLabs URL] → Use video URL directly
    ↓
[Sync Labs API] → Submit with original video URL + dubbed audio URL
    ↓
[Poll Status] → Check until complete
    ↓
[Download Result] → Final lip-synced video
```

---

## n8n Configuration: Upload Files to file.io

### Node 1: Upload Audio to file.io

After extracting audio from FFmpeg:

**HTTP Request Node:**
- **Method:** `POST`
- **URL:** `https://file.io`
- **Send Binary Data:** ON
- **Binary Property:** `audio` (or whatever you named it)
- **Response Format:** JSON

**Save the response:**
- Output will have: `{{ $json.link }}` (the public URL)

### Node 2: Upload Video to file.io

**HTTP Request Node:**
- **Method:** `POST`
- **URL:** `https://file.io`
- **Send Binary Data:** ON
- **Binary Property:** `video` (or whatever you named it)
- **Response Format:** JSON

**Save the response:**
- Output will have: `{{ $json.link }}` (the public URL)

---

## n8n Configuration: Submit to Sync Labs

### Node 3: Create Sync Labs Job

**HTTP Request Node:**

**Authentication:**
- **Authentication:** Generic Credential Type
- **Header Auth**
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
      "url": "{{ $('Upload Video').item.json.link }}"
    },
    {
      "type": "audio",
      "url": "{{ $('Upload Audio').item.json.link }}"
    }
  ]
}
```

**Response:**
- You'll get a `job_id` in the response
- Save this: `{{ $json.id }}`

---

## n8n Configuration: Poll for Completion

### Node 4: Wait for Job Completion

**Loop Until Job Complete:**

You need to poll the status endpoint until the job is done. Two options:

#### Option A: Use n8n Wait Node + Loop

1. **Wait Node** (1 minute)
2. **HTTP Request: Check Status**
   - Method: `GET`
   - URL: `https://api.sync.so/v2/generate/{{ $json.id }}`
   - Headers: `x-api-key: YOUR_API_KEY`
3. **IF Node** - Check if `{{ $json.status }}` === `"completed"`
   - If not complete: Loop back to Wait node
   - If complete: Continue to download

#### Option B: Use n8n Webhook (Recommended)

When creating the job, add a webhook URL:

```json
{
  "model": "lipsync-2",
  "input": [...],
  "webhookUrl": "https://your-n8n-webhook-url"
}
```

Sync Labs will POST to this URL when complete!

---

## n8n Configuration: Download Result

### Node 5: Download Final Video

Once job is complete, the response contains:

```json
{
  "id": "job-id",
  "status": "completed",
  "output": [
    {
      "url": "https://sync-labs-output-url.mp4"
    }
  ]
}
```

**HTTP Request Node:**
- **Method:** `GET`
- **URL:** `{{ $json.output[0].url }}`
- **Response Format:** `File`

**Output:** Final lip-synced video!

---

## Complete n8n Workflow Example

```
1. [Webhook/Trigger] → Start workflow

2. [Get dubbed video from ElevenLabs]
   └─ Output: Video binary with dubbed audio

3. [HTTP Request: FFmpeg Microservice]
   ├─ URL: /process-inline
   └─ Output: ZIP with audio.mp3 + video.mp4

4. [Compression] → Decompress ZIP
   └─ Output: Separate audio and video binaries

5. [HTTP Request: Upload Audio to file.io]
   ├─ POST https://file.io
   ├─ Send Binary Data: ON
   └─ Output: { "link": "https://file.io/abc123" }

6. [HTTP Request: Upload Video to file.io]
   ├─ POST https://file.io
   ├─ Send Binary Data: ON
   └─ Output: { "link": "https://file.io/xyz789" }

7. [HTTP Request: Submit to Sync Labs]
   ├─ POST https://api.sync.so/v2/generate
   ├─ Body: { "model": "lipsync-2", "input": [...] }
   └─ Output: { "id": "job-abc-123" }

8. [Wait] → 60 seconds

9. [HTTP Request: Check Status]
   ├─ GET https://api.sync.so/v2/generate/{{ $json.id }}
   └─ Output: { "status": "completed", "output": [...] }

10. [IF] → Is status = "completed"?
    ├─ No → Loop back to step 8
    └─ Yes → Continue

11. [HTTP Request: Download Result]
    ├─ GET {{ $json.output[0].url }}
    └─ Output: Final lip-synced video binary

12. [Send to destination] → Email, S3, webhook, etc.
```

---

## Alternative: Skip FFmpeg if You Have URLs

If ElevenLabs gives you a URL to the dubbed video:

```
1. [Get ElevenLabs dubbed video URL]

2. [HTTP Request: Submit to Sync Labs]
   ├─ POST https://api.sync.so/v2/generate
   ├─ Body: {
   │   "model": "lipsync-2",
   │   "input": [
   │     { "type": "video", "url": "ORIGINAL_VIDEO_URL" },
   │     { "type": "audio", "url": "ELEVENLABS_DUBBED_AUDIO_URL" }
   │   ]
   │ }
   └─ Output: job_id

3. [Poll for completion...]

4. [Download result]
```

**This skips FFmpeg entirely if you have direct URLs!**

---

## file.io API Details

**Free tier:**
- 100MB max file size
- Files auto-delete after download
- No signup required
- Perfect for temporary workflow files

**Alternative Services:**
- **tmpfiles.org** - Similar temporary hosting
- **AWS S3 with pre-signed URLs** - More reliable
- **Cloudinary** - Video-optimized storage

---

## Troubleshooting

### Error: "Invalid audio URL"
- Ensure the URL is publicly accessible
- Test the URL in a browser first
- file.io URLs expire after one download

### Error: "Video too large"
- Sync Labs has file size limits
- Compress video before uploading
- Check their pricing for higher limits

### Job stuck in "processing"
- Large videos take time (can be 5-10+ minutes)
- Keep polling every 30-60 seconds
- Check Sync Labs dashboard for job status

### file.io upload fails
- File might be too large (>100MB)
- Try AWS S3 or another service instead

---

## Cost Optimization

**Free Tier Services:**
- file.io (temporary storage)
- Railway.app free tier (FFmpeg microservice)

**Paid Services:**
- Sync Labs API (check their pricing)
- AWS S3 (very cheap for temporary storage)

**Webhook vs Polling:**
- Webhook is more efficient (no repeated API calls)
- Set up an n8n webhook endpoint
- Sync Labs will notify you when done

---

## Security Notes

- Don't expose your Sync Labs API key
- Use n8n credentials manager
- file.io files are public URLs - don't upload sensitive content
- Consider using pre-signed S3 URLs for production

---

## Next Steps

1. ✅ Get Sync Labs API key
2. ✅ Test file.io uploads manually
3. ✅ Build n8n workflow step by step
4. ✅ Test with a small video first
5. ✅ Optimize timing and polling intervals

---

## Questions to Answer

Before building the workflow, clarify:

1. **Does ElevenLabs give you URLs or binary files?**
   - If URLs → Skip FFmpeg, use directly
   - If binary → Use FFmpeg + file.io workflow

2. **Do you have AWS S3 or other cloud storage?**
   - If yes → More reliable than file.io
   - If no → file.io works fine for testing

3. **How large are your videos?**
   - <100MB → file.io OK
   - >100MB → Need S3 or Cloudinary

4. **Production vs Testing?**
   - Testing → file.io + polling is fine
   - Production → S3 + webhooks recommended
