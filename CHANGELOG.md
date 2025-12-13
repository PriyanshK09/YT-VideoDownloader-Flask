# Changelog

## [2024-12-13] - Bot Detection Fix

### Fixed
- **Fixed "This request was detected as a bot" error**
  - Explicitly use ANDROID_VR client which doesn't require po_token
  - Removed deprecated `use_po_token` parameter
  - Added configurable YouTube client via environment variable
  
### Added
- `.env.example` file for configuration documentation
- `YOUTUBE_CLIENT` environment variable (default: ANDROID_VR)
- `YOUTUBE_USE_OAUTH` environment variable for optional OAuth authentication

### Technical Changes
- Updated both `app.py` and `production.py`:
  - Added `client` parameter to YouTube() initialization
  - Set default client to ANDROID_VR (doesn't require po_token)
  - Removed deprecated `use_po_token` parameter
  - Added dotenv support for environment variable loading
  
### Benefits
- Bypasses YouTube bot detection without requiring po_token
- More reliable video fetching
- Cleaner implementation using non-deprecated features
- Configurable client selection via environment variables

## [2024-12-13] - YouTube Video Fetching Fix

### Changed
- **Replaced yt-dlp with pytubefix** for better YouTube API compatibility
  - yt-dlp was failing with "Failed to extract any player response" errors
  - pytubefix is a more actively maintained library with better YouTube support
  - Simplified code by removing complex fallback strategies and client configurations

### Fixed
- Fixed YouTube video information extraction in production environment
- Fixed "Failed to extract any player response" error
- Updated gunicorn from 21.2.0 to 22.0.0 to fix security vulnerabilities:
  - HTTP Request/Response Smuggling vulnerability
  - Request smuggling leading to endpoint restriction bypass

### Technical Changes
- Updated `requirements.txt`:
  - Removed: `yt-dlp==2025.12.8`
  - Added: `pytubefix==10.3.6`
  - Updated: `gunicorn==21.2.0` → `gunicorn==22.0.0`
  
- Simplified both `production.py` and `app.py`:
  - Removed complex yt-dlp configuration with multiple client fallback strategies
  - Removed 70+ lines of configuration code
  - Simplified video extraction logic using pytubefix's cleaner API
  - Maintained all existing functionality (caching, error handling, format selection)

### Benefits
- More reliable video fetching on production
- Cleaner, more maintainable code (reduced by ~340 lines)
- Better error messages
- Improved security with updated dependencies
- Faster video information extraction

### Migration Notes
- No breaking changes to API endpoints
- Frontend remains unchanged
- Docker deployment remains the same (FFmpeg still available but not required)
