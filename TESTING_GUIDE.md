# Testing Guide for YouTube Video Downloader Fix

## Overview
This guide explains how to test the YouTube video downloader after the migration from yt-dlp to pytubefix.

## What Changed
- **Library**: Replaced `yt-dlp` with `pytubefix`
- **Reason**: yt-dlp was failing with "Failed to extract any player response" errors
- **Impact**: More reliable video fetching with cleaner, simpler code

## Local Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Development Server
```bash
python app.py
```

### 3. Test in Browser
1. Open http://localhost:5000
2. Test with various YouTube URLs:
   - Standard video: `https://www.youtube.com/watch?v=VIDEO_ID`
   - Short URL: `https://youtu.be/VIDEO_ID`
   - With query params: `https://youtu.be/VIDEO_ID?si=PARAM`

### 4. Expected Behavior
- Video information should load successfully
- Thumbnail should display
- Multiple quality options should be available (1080p, 720p, 480p, etc.)
- Audio-only option should be available
- Downloads should work for all formats

## Testing Endpoints

### Health Check
```bash
curl http://localhost:5000/health
# Expected: {"status": "healthy", "timestamp": <unix_timestamp>}
```

### Video Info
```bash
curl -X POST http://localhost:5000/get_video_info \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}'
```

Expected response:
```json
{
  "title": "Video Title",
  "thumbnail": "https://...",
  "formats": [
    {
      "type": "video",
      "quality": "720p",
      "mime_type": "video/mp4",
      "itag": "22",
      "filesize_mb": 50.5,
      "format_id": "22",
      "ext": "mp4"
    },
    {
      "type": "audio",
      "quality": "MP3 128kbps",
      "mime_type": "audio/mp4",
      "itag": "140",
      "filesize_mb": 5.2,
      "format_id": "140",
      "ext": "mp4"
    }
  ]
}
```

## Production Deployment Testing

### 1. Verify Requirements
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
gunicorn --version  # Should be 22.0.0 or higher
```

### 2. Run Production Server
```bash
python production.py
```

### 3. Test with Production Settings
- Cache should work (same video fetched twice should be faster)
- Error handling should be graceful
- Logs should show INFO level messages

## Edge Cases to Test

### Valid URLs
- ✅ `https://www.youtube.com/watch?v=VIDEO_ID`
- ✅ `https://youtu.be/VIDEO_ID`
- ✅ `https://www.youtube.com/watch?v=VIDEO_ID&t=100s`
- ✅ `https://youtu.be/VIDEO_ID?si=PARAM`

### Invalid URLs
- ❌ `https://www.google.com` (should return "Invalid YouTube URL")
- ❌ `not-a-url` (should return "Invalid YouTube URL")
- ❌ Empty URL (should return "URL cannot be empty")

### Error Cases
- Private videos (should return appropriate error message)
- Deleted videos (should return appropriate error message)
- Age-restricted videos (may or may not work depending on pytubefix capabilities)

## Performance Testing

### Cache Test
1. Fetch video info for a URL
2. Fetch same URL again within 1 hour
3. Second request should be significantly faster (cached)

### Concurrent Requests
Test with multiple simultaneous requests to ensure stability:
```bash
# Test with Apache Bench (if available)
ab -n 100 -c 10 http://localhost:5000/health
```

## Security Testing

### Input Validation
- Test with malformed URLs
- Test with very long URLs
- Test with special characters

### Security Headers
The application should:
- Validate all input URLs
- Sanitize output
- Handle errors gracefully without exposing sensitive info

## Troubleshooting

### Issue: "No module named 'pytubefix'"
**Solution**: Run `pip install -r requirements.txt`

### Issue: Video info fails to load
**Solution**: 
1. Check internet connectivity
2. Verify the video is publicly accessible
3. Check logs for specific error messages

### Issue: Downloads are slow
**Solution**: This is normal for large videos. Consider:
- Using lower quality formats
- Checking network connection
- Verifying server resources

## Monitoring

### Key Metrics to Monitor
- Response time for `/get_video_info` endpoint
- Success rate of video fetches
- Cache hit rate
- Error rate and types

### Logs to Watch
- `INFO:__main__:Successfully extracted video info for: <title>`
- `ERROR:__main__:pytubefix error: <error>`
- `ERROR:__main__:Error processing YouTube video: <error>`

## Rollback Plan

If issues arise, rollback by:
1. Revert to previous commit: `git checkout <previous-commit-hash>`
2. Reinstall old requirements: `pip install yt-dlp==2025.12.8`
3. Deploy previous version

## Support

For issues related to:
- **pytubefix**: https://github.com/JuanBindez/pytubefix
- **Flask**: https://flask.palletsprojects.com/
- **Gunicorn**: https://docs.gunicorn.org/
