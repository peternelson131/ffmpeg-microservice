#!/bin/bash

# FFmpeg Microservice Test Script
# Usage: ./test_service.sh [base_url] [video_file]

# Default values
BASE_URL="${1:-http://localhost:8080}"
VIDEO_FILE="${2:-test.mp4}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "FFmpeg Microservice Test Script"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Video File: $VIDEO_FILE"
echo "=========================================="
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
echo "GET $BASE_URL/health"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Health check successful${NC}"
    echo "Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi
echo ""

# Check if video file exists
if [ ! -f "$VIDEO_FILE" ]; then
    echo -e "${RED}✗ Video file not found: $VIDEO_FILE${NC}"
    echo "Please provide a valid video file as the second argument"
    echo "Usage: ./test_service.sh [base_url] [video_file]"
    exit 1
fi

# Test 2: Extract Audio
echo -e "${YELLOW}Test 2: Extract Audio${NC}"
echo "POST $BASE_URL/extract-audio"
curl -X POST "$BASE_URL/extract-audio" \
  -F "video=@$VIDEO_FILE" \
  -o test_audio.mp3 \
  --progress-bar

if [ $? -eq 0 ] && [ -f test_audio.mp3 ]; then
    AUDIO_SIZE=$(ls -lh test_audio.mp3 | awk '{print $5}')
    echo -e "${GREEN}✓ Audio extraction successful${NC}"
    echo "Output: test_audio.mp3 ($AUDIO_SIZE)"
else
    echo -e "${RED}✗ Audio extraction failed${NC}"
fi
echo ""

# Test 3: Extract Video
echo -e "${YELLOW}Test 3: Extract Video (No Audio)${NC}"
echo "POST $BASE_URL/extract-video"
curl -X POST "$BASE_URL/extract-video" \
  -F "video=@$VIDEO_FILE" \
  -o test_video.mp4 \
  --progress-bar

if [ $? -eq 0 ] && [ -f test_video.mp4 ]; then
    VIDEO_SIZE=$(ls -lh test_video.mp4 | awk '{print $5}')
    echo -e "${GREEN}✓ Video extraction successful${NC}"
    echo "Output: test_video.mp4 ($VIDEO_SIZE)"
else
    echo -e "${RED}✗ Video extraction failed${NC}"
fi
echo ""

# Test 4: Process Inline (ZIP)
echo -e "${YELLOW}Test 4: Process Inline (ZIP with both files)${NC}"
echo "POST $BASE_URL/process-inline"
curl -X POST "$BASE_URL/process-inline" \
  -F "video=@$VIDEO_FILE" \
  -o test_processed.zip \
  --progress-bar

if [ $? -eq 0 ] && [ -f test_processed.zip ]; then
    ZIP_SIZE=$(ls -lh test_processed.zip | awk '{print $5}')
    echo -e "${GREEN}✓ Process inline successful${NC}"
    echo "Output: test_processed.zip ($ZIP_SIZE)"

    # Try to extract ZIP to see contents
    if command -v unzip &> /dev/null; then
        echo "ZIP contents:"
        unzip -l test_processed.zip
    fi
else
    echo -e "${RED}✗ Process inline failed${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}Test Summary${NC}"
echo "=========================================="
echo "Generated files:"
ls -lh test_audio.mp3 test_video.mp4 test_processed.zip 2>/dev/null || echo "No files generated"
echo ""
echo "Test complete!"
echo ""
echo "To clean up test files, run:"
echo "rm test_audio.mp3 test_video.mp4 test_processed.zip"
