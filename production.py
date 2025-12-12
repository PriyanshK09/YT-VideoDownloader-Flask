from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import re
from io import BytesIO
from urllib.parse import urlparse, parse_qs
import logging
import tempfile
import shutil
from functools import lru_cache
import hashlib
import json
import time

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Production configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
app.config['TEMPLATES_AUTO_RELOAD'] = False

# Cache configuration
CACHE_DIR = tempfile.mkdtemp(prefix='youtube_cache_')
CACHE_DURATION = 3600  # 1 hour cache

# Optimized yt-dlp configuration for production
YDL_OPTS_FAST = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'no_download': True,
    'format': 'best[height<=1080]/best',
    'noplaylist': True,
    'extractaudio': False,
    'socket_timeout': 15,
    'retries': 2,
    'fragment_retries': 2,
    'skip_unavailable_fragments': True,
    'ignoreerrors': True,
    'no_check_certificates': True,
}

def get_cache_key(url):
    """Generate cache key for URL"""
    return hashlib.md5(url.encode()).hexdigest()

def get_cached_info(cache_key):
    """Get cached video info"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            # Check if cache is still valid
            if time.time() - data['timestamp'] < CACHE_DURATION:
                return data['info']
        except:
            pass
    return None

def cache_info(cache_key, info):
    """Cache video info"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump({
                'info': info,
                'timestamp': time.time()
            }, f)
    except:
        pass

def is_valid_youtube_url(url):
    """Check if the URL is a valid YouTube URL."""
    youtube_regex = (
        r'^((?:https?:)?\/\/)?((?:www|m)\.)?'
        r'(youtube\.com|youtu\.be|youtube-nocookie\.com)'
        r'(\/.*[\?&]v=|\/v\/|\/embed\/|\/shorts\/|\/watch\?v=|\/watch\?.+&v=)'
        r'([^#\&\?\n\s]{11})'
    )
    match = re.match(youtube_regex, url, re.IGNORECASE)
    if not match:
        youtu_be_regex = r'^(https?:\/\/)?(www\.)?(youtu\.be\/|youtube\.com\/(embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})(\S*)$'
        return bool(re.match(youtu_be_regex, url, re.IGNORECASE))
    return True

def extract_video_id(url):
    """Extract video ID from YouTube URL."""
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1].split('?')[0]
            
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc:
            if 'v' in parse_qs(parsed.query):
                return parse_qs(parsed.query)['v'][0]
            elif 'embed' in parsed.path:
                return parsed.path.split('/')[-1]
        
        path_segments = [s for s in parsed.path.split('/') if s]
        if path_segments and len(path_segments[-1]) == 11:
            return path_segments[-1]
            
        video_id_match = re.search(r'[0-9A-Za-z_-]{11}', url)
        if video_id_match:
            return video_id_match.group(0)
            
        return None
    except Exception as e:
        logger.error(f"Error extracting video ID: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
            
        url = data['url'].strip()
        
        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400
            
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL. Please enter a valid YouTube video URL.'}), 400
        
        try:
            video_id = extract_video_id(url)
            
            if not video_id or len(video_id) != 11:
                return jsonify({'error': 'Could not extract video ID from URL'}), 400
                
            clean_url = f'https://www.youtube.com/watch?v={video_id}'
            
            # Check cache first
            cache_key = get_cache_key(clean_url)
            cached_info = get_cached_info(cache_key)
            if cached_info:
                return jsonify(cached_info)
            
            try:
                # Extract video information with optimized settings
                with yt_dlp.YoutubeDL(YDL_OPTS_FAST) as ydl:
                    info = ydl.extract_info(clean_url, download=False)
                    
                # Get video title and thumbnail
                title = info.get('title', 'Unknown Title')
                thumbnail = info.get('thumbnail', f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg')
                
                # Get available formats - optimized for speed
                formats = []
                
                # Pre-defined quality priorities for faster processing
                quality_priorities = ['1080p', '720p', '480p', '360p', '240p']
                seen_formats = set()
                
                # Process formats more efficiently
                for fmt in info.get('formats', []):
                    if (fmt.get('vcodec') != 'none' and 
                        fmt.get('acodec') != 'none' and
                        fmt.get('ext') in ['mp4'] and
                        fmt.get('height') and
                        fmt.get('format_id')):
                        
                        quality = f"{fmt.get('height')}p"
                        if quality not in seen_formats and quality in quality_priorities:
                            seen_formats.add(quality)
                            filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                            
                            formats.append({
                                'type': 'video',
                                'quality': quality,
                                'mime_type': "video/mp4",
                                'itag': str(fmt.get('format_id')),
                                'filesize_mb': round(filesize / (1024 * 1024), 1) if filesize else None,
                                'format_id': fmt.get('format_id'),
                                'ext': 'mp4'
                            })
                
                # Sort by quality priority
                formats.sort(key=lambda x: quality_priorities.index(x['quality']) if x['quality'] in quality_priorities else 99)
                
                # Get best audio format
                for fmt in info.get('formats', []):
                    if (fmt.get('vcodec') == 'none' and 
                        fmt.get('acodec') != 'none' and
                        fmt.get('ext') in ['mp4', 'm4a'] and
                        fmt.get('format_id')):
                        
                        abr = fmt.get('abr', 0)
                        quality = f"MP3 {int(abr)}kbps" if abr else "MP3"
                        filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                        
                        formats.append({
                            'type': 'audio',
                            'quality': quality,
                            'mime_type': "audio/mp4",
                            'itag': str(fmt.get('format_id')),
                            'filesize_mb': round(filesize / (1024 * 1024), 1) if filesize else None,
                            'format_id': fmt.get('format_id'),
                            'ext': 'mp4'
                        })
                        break
                
                if not formats:
                    return jsonify({
                        'error': 'No downloadable formats found. The video may have restrictions.'
                    }), 400
                
                video_info = {
                    'title': title,
                    'thumbnail': thumbnail,
                    'formats': formats
                }
                
                # Cache the result
                cache_info(cache_key, video_info)
                
                return jsonify(video_info)
                
            except Exception as e:
                logger.error(f"yt-dlp error: {str(e)}")
                return jsonify({
                    'error': f'Error accessing YouTube: {str(e)}'
                }), 400
                
        except Exception as e:
            logger.error(f"Error processing YouTube video: {str(e)}")
            return jsonify({
                'error': f'Error processing YouTube video: {str(e)}'
            }), 400
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500

@app.route('/download', methods=['GET'])
def download():
    try:
        url = request.args.get('url')
        format_id = request.args.get('itag')
        
        if not url or not format_id:
            return jsonify({'error': 'Missing URL or format ID parameter'}), 400
            
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
            
        try:
            # Create a temporary directory for downloads
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Optimized yt-dlp options for download
                ydl_opts_download = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': format_id,
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'noplaylist': True,
                    'extractaudio': False,
                    'socket_timeout': 30,
                    'retries': 3,
                    'fragment_retries': 3,
                    'skip_unavailable_fragments': True,
                    'ignoreerrors': True,
                    'no_check_certificates': True,
                    'http_chunk_size': 8192,
                }
                
                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                # Find the downloaded file
                downloaded_file = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if not file.endswith('.part'):
                            downloaded_file = os.path.join(root, file)
                            break
                    if downloaded_file:
                        break
                
                if not downloaded_file or not os.path.exists(downloaded_file):
                    return jsonify({'error': 'Download failed or file not found'}), 500
                
                # Get file info
                filename = os.path.basename(downloaded_file)
                
                # Read the file into memory
                with open(downloaded_file, 'rb') as f:
                    file_data = f.read()
                
                # Determine MIME type
                if filename.endswith('.mp4'):
                    mime_type = 'video/mp4'
                elif filename.endswith('.webm'):
                    mime_type = 'video/webm'
                elif filename.endswith('.mp3') or filename.endswith('.m4a'):
                    mime_type = 'audio/mp4'
                else:
                    mime_type = 'application/octet-stream'
                
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Send the file
                return send_file(
                    BytesIO(file_data),
                    as_attachment=True,
                    download_name=filename,
                    mimetype=mime_type
                )
                
            except Exception as e:
                # Clean up temporary directory on error
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise e
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return jsonify({
                'error': f'Error downloading video: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in download: {str(e)}")
        return jsonify({
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
