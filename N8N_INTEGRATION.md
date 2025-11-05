# n8n Cloud Integration Guide

Complete guide to integrate the FFmpeg microservice with n8n Cloud.

## Issue: "No video file provided"

This error means n8n isn't sending the video file correctly in the multipart/form-data request.

## Solution: Proper HTTP Request Configuration

### Method 1: Using Binary Data Directly

**HTTP Request Node Settings:**

1. **Method:** `POST`
2. **URL:** `https://ffmpeg-microservice-production.up.railway.app/extract-audio`
3. **Send Binary Data:** Toggle **ON**
4. **Binary Property:** Name of your binary data field from previous node (usually `data`)
5. **Response Format:** `File`

**This is the simplest method - n8n automatically sends binary data as multipart/form-data when "Send Binary Data" is enabled.**

### Method 2: Manual Form-Data Configuration

If Method 1 doesn't work:

1. **Method:** `POST`
2. **URL:** `https://ffmpeg-microservice-production.up.railway.app/extract-audio`
3. **Send Binary Data:** Toggle **OFF**
4. Click **"Add Option"** → **"Body Content Type"** → Select `Form-Data Multipart`
5. **Body Parameters:**
   - Click **"Add Parameter"**
   - **Name:** `video`
   - **Input Data Field Name:** Enter the name of your binary property (e.g., `data`)
6. **Response Format:** `File`

### Method 3: Using Code Node as Proxy

If neither method works, use a Code node to prepare the request:

```javascript
// Code Node (JavaScript)
const binaryData = items[0].binary.data; // Replace 'data' with your binary property name

return {
  json: {},
  binary: {
    video: binaryData
  }
};
```

Then in HTTP Request node:
- **Send Binary Data:** ON
- **Binary Property:** `video`

## Complete Example Workflow

### Scenario: ElevenLabs → FFmpeg → Sync Labs

```
1. [HTTP Request] → Get video from ElevenLabs
   └─ Output: Binary video in `data` property

2. [HTTP Request] → Send to FFmpeg Microservice
   ├─ Method: POST
   ├─ URL: https://ffmpeg-microservice-production.up.railway.app/extract-audio
   ├─ Send Binary Data: ON
   ├─ Binary Property: data
   └─ Response Format: File
   └─ Output: MP3 audio in `data` property

3. [HTTP Request] → Send audio to Sync Labs
   └─ Use the extracted audio
```

## Debugging Steps

### Step 1: Check Binary Data

Before the HTTP Request node, add a **"Sticky Note"** and check:
- Does the previous node output binary data?
- What is the property name? (Look in the node output)

### Step 2: Test with Simple Data First

Create a test workflow:
1. **"Read Binary Files"** node → Load a local MP4 file
2. **HTTP Request** node → Send to FFmpeg service
   - Send Binary Data: ON
   - Binary Property: data

### Step 3: Check Binary Property Name

Click "Execute Node" on the previous node and inspect the output:
```json
{
  "json": {},
  "binary": {
    "data": {           ← This is your property name
      "fileName": "video.mp4",
      "mimeType": "video/mp4"
    }
  }
}
```

Use this name in the "Binary Property" field.

## Common Mistakes

### ❌ Wrong: Using Expression for Binary Data
```
Body Parameters:
  Name: video
  Value: {{ $binary.data }}  ← This won't work
```

### ✅ Correct: Enable "Send Binary Data"
```
Send Binary Data: ON
Binary Property: data
```

### ❌ Wrong: Body Content Type set manually with binary
```
Body Content Type: Form-Data Multipart
Send Binary Data: OFF
```

### ✅ Correct: Let n8n handle it
```
Send Binary Data: ON
(Body Content Type is automatic)
```

## Alternative Endpoints

Depending on your needs:

### Extract Audio Only (MP3)
```
URL: /extract-audio
Output: MP3 file
```

### Extract Video Only (No Audio)
```
URL: /extract-video
Output: MP4 file without audio
```

### Extract Both (ZIP)
```
URL: /process-inline
Output: ZIP file with both MP3 and MP4
```

After extraction, you'll need to unzip in n8n using:
- **"Compression"** node → Mode: Decompress

## Testing Directly from n8n

### Test URL
```bash
curl https://ffmpeg-microservice-production.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "ffmpeg_available": true,
  "version": "1.0.0"
}
```

### Test with Sample File

1. Use **"Read Binary Files"** node to load a test video
2. Configure HTTP Request as shown above
3. Add **"Write Binary File"** node to save the output
4. Execute and verify the MP3 was created

## Advanced: Custom Headers (If Needed)

If you need to add authentication later:

**Headers:**
- Name: `X-API-Key`
- Value: `your-api-key`

(Not currently needed - service has no auth)

## Troubleshooting

### Error: "No video file provided"
- **Cause:** Binary data not sent or wrong property name
- **Fix:** Enable "Send Binary Data" and verify binary property name

### Error: "File too large"
- **Cause:** Video exceeds 500MB limit
- **Fix:** Split video or increase MAX_CONTENT_LENGTH in app.py

### Error: "Invalid file type"
- **Cause:** File is not a supported video format
- **Fix:** Ensure file is MP4, AVI, MOV, MKV, WebM, or FLV

### Error: "Processing failed"
- **Cause:** FFmpeg error or corrupted video
- **Fix:** Check Railway logs or test with different video

### Connection Timeout
- **Cause:** Large video taking too long to process
- **Fix:** Increase timeout in n8n HTTP Request node options

## Need Help?

1. Check the binary property name in your previous node output
2. Try Method 1 first (simplest)
3. Test with a small video file first
4. Check Railway logs for detailed error messages

## Example n8n Workflow JSON

You can import this test workflow:

```json
{
  "nodes": [
    {
      "name": "Start",
      "type": "n8n-nodes-base.start",
      "position": [250, 300]
    },
    {
      "name": "Read Video File",
      "type": "n8n-nodes-base.readBinaryFiles",
      "position": [450, 300],
      "parameters": {
        "filePath": "=/tmp/test.mp4"
      }
    },
    {
      "name": "Extract Audio",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300],
      "parameters": {
        "method": "POST",
        "url": "https://ffmpeg-microservice-production.up.railway.app/extract-audio",
        "sendBinaryData": true,
        "binaryPropertyName": "data",
        "options": {
          "response": {
            "response": {
              "responseFormat": "file"
            }
          }
        }
      }
    }
  ]
}
```
