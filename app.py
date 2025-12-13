from flask import Flask, render_template, request, jsonify, send_file, Response
from pytubefix import YouTube
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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# YouTube client configuration
YOUTUBE_USE_OAUTH = os.getenv('YOUTUBE_USE_OAUTH', 'false').lower() == 'true'
YOUTUBE_USE_PO_TOKEN = os.getenv('YOUTUBE_USE_PO_TOKEN', 'true').lower() == 'true'

# Cache configuration
CACHE_DIR = tempfile.mkdtemp(prefix='youtube_cache_')
CACHE_DURATION = 3600  # 1 hour cache

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
        # Try to match youtu.be URLs
        youtu_be_regex = r'^(https?:\/\/)?(www\.)?(youtu\.be\/|youtube\.com\/(embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})(\S*)$'
        return bool(re.match(youtu_be_regex, url, re.IGNORECASE))
    return True

def extract_video_id(url):
    """Extract video ID from YouTube URL."""
    try:
        # Handle youtu.be URLs
        if 'youtu.be' in url:
            return url.split('/')[-1].split('?')[0]
            
        # Handle youtube.com URLs
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc:
            if 'v' in parse_qs(parsed.query):
                return parse_qs(parsed.query)['v'][0]
            elif 'embed' in parsed.path:
                return parsed.path.split('/')[-1]
        
        # Try to extract from path
        path_segments = [s for s in parsed.path.split('/') if s]
        if path_segments and len(path_segments[-1]) == 11:
            return path_segments[-1]
            
        # Last resort: try to find an 11-character video ID in the URL
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
        logger.debug(f"Received request: {request.get_data()}")
        
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
            
        url = data['url'].strip()
        logger.debug(f"Processing URL: {url}")
        
        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400
            
        if not is_valid_youtube_url(url):
            logger.error(f"Invalid YouTube URL: {url}")
            return jsonify({'error': 'Invalid YouTube URL. Please enter a valid YouTube video URL.'}), 400
        
        try:
            # Extract video ID and create a clean URL
            video_id = extract_video_id(url)
            logger.debug(f"Extracted video ID: {video_id}")
            
            if not video_id or len(video_id) != 11:
                logger.error(f"Invalid video ID: {video_id}")
                return jsonify({'error': 'Could not extract video ID from URL'}), 400
                
            clean_url = f'https://www.youtube.com/watch?v={video_id}'
            logger.debug(f"Clean URL: {clean_url}")
            
            # Check cache first
            cache_key = get_cache_key(clean_url)
            cached_info = get_cached_info(cache_key)
            if cached_info:
                logger.debug("Returning cached info")
                return jsonify(cached_info)
            
            try:
                # Extract video information using pytubefix
                logger.info(f"Attempting extraction with pytubefix (use_po_token={YOUTUBE_USE_PO_TOKEN}, use_oauth={YOUTUBE_USE_OAUTH})")
                yt = YouTube(clean_url, use_po_token=YOUTUBE_USE_PO_TOKEN, use_oauth=YOUTUBE_USE_OAUTH, allow_oauth_cache=True)
                
                # Get video title and thumbnail
                title = yt.title
                thumbnail = yt.thumbnail_url
                
                logger.debug(f"Video title: {title}")
                
                # Get available formats
                formats = []
                
                # Pre-defined quality priorities for faster processing
                quality_priorities = ['1080p', '720p', '480p', '360p', '240p']
                seen_formats = set()
                
                # Get progressive streams (video + audio combined)
                progressive_streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
                
                for stream in progressive_streams:
                    if stream.resolution:
                        quality = stream.resolution
                        if quality not in seen_formats and quality in quality_priorities:
                            seen_formats.add(quality)
                            filesize = stream.filesize
                            
                            formats.append({
                                'type': 'video',
                                'quality': quality,
                                'mime_type': stream.mime_type,
                                'itag': str(stream.itag),
                                'filesize_mb': round(filesize / (1024 * 1024), 1) if filesize and filesize > 0 else None,
                                'format_id': str(stream.itag),
                                'ext': 'mp4'
                            })
                
                # Sort by quality priority
                formats.sort(key=lambda x: quality_priorities.index(x['quality']) if x['quality'] in quality_priorities else 99)
                
                # Get best audio format
                audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
                if audio_streams:
                    audio_stream = audio_streams.first()
                    if audio_stream:
                        abr = audio_stream.abr if hasattr(audio_stream, 'abr') and audio_stream.abr else None
                        quality = f"MP3 {abr}" if abr else "MP3"
                        filesize = audio_stream.filesize
                        
                        formats.append({
                            'type': 'audio',
                            'quality': quality,
                            'mime_type': audio_stream.mime_type,
                            'itag': str(audio_stream.itag),
                            'filesize_mb': round(filesize / (1024 * 1024), 1) if filesize and filesize > 0 else None,
                            'format_id': str(audio_stream.itag),
                            'ext': 'mp4'
                        })
                
                logger.debug(f"Found {len(formats)} downloadable formats")
                
                if not formats:
                    logger.error("No downloadable formats found")
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
                
                logger.info(f"Successfully extracted video info for: {title}")
                return jsonify(video_info)
                
            except Exception as e:
                logger.error(f"pytubefix error: {str(e)}")
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
        itag = request.args.get('itag')
        
        if not url or not itag:
            return jsonify({'error': 'Missing URL or format ID parameter'}), 400
            
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
            
        try:
            # Create a temporary directory for downloads
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Download the video using pytubefix
                logger.info(f"Attempting download with pytubefix (use_po_token={YOUTUBE_USE_PO_TOKEN}, use_oauth={YOUTUBE_USE_OAUTH})")
                yt = YouTube(url, use_po_token=YOUTUBE_USE_PO_TOKEN, use_oauth=YOUTUBE_USE_OAUTH, allow_oauth_cache=True)
                
                # Get the stream with the specified itag
                stream = yt.streams.get_by_itag(int(itag))
                
                if not stream:
                    return jsonify({'error': 'Invalid format ID or stream not found'}), 400
                
                # Download to temporary directory
                logger.info(f"Downloading stream with itag: {itag}")
                output_path = stream.download(output_path=temp_dir)
                
                if not output_path or not os.path.exists(output_path):
                    return jsonify({'error': 'Download failed or file not found'}), 500
                
                # Get file info
                filename = os.path.basename(output_path)
                
                logger.info(f"Download complete: {filename}")
                
                # Read the file into memory
                with open(output_path, 'rb') as f:
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
