# YouTube Video Downloader - Render Deployment Guide

## Prerequisites

1. **Install Render CLI**
   ```bash
   npm install -g @render/cli
   ```

2. **Login to Render**
   ```bash
   render login
   ```

3. **Git Repository**
   - Make sure your code is in a Git repository
   - Push to GitHub/GitLab (required for Render)

## Quick Deployment

### Option 1: Using Render CLI (Recommended)

1. **Initialize your project**
   ```bash
   cd /home/priyansh/Downloads/myapp
   git init
   git add .
   git commit -m "Initial commit - YouTube Downloader"
   ```

2. **Create GitHub repository**
   ```bash
   # Create repo on GitHub first, then:
   git remote add origin https://github.com/PriyanshK09/youtube-downloader.git
   git push -u origin main
   ```

3. **Deploy with Render CLI**
   ```bash
   render deploy
   ```

### Option 2: Manual Setup

1. **Create Render Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure settings (see below)

## Configuration Details

### Render Web Service Settings

- **Name**: `youtube-downloader`
- **Environment**: `Docker`
- **Branch**: `main`
- **Root Directory**: `.`
- **Dockerfile Path**: `./Dockerfile`
- **Instance Type**: `Free` (or `Standard` for better performance)
- **Health Check Path**: `/health`

### Environment Variables

| Key | Value | Description |
|-----|-------|-------------|
| `PORT` | `5000` | Port for the Flask application |
| `PYTHON_VERSION` | `3.11` | Python runtime version |
| `YOUTUBE_CLIENT` | `ANDROID_VR` | YouTube client (helps avoid bot detection) |
| `YOUTUBE_USE_OAUTH` | `false` | Enable OAuth authentication (optional) |

## Files Created for Deployment

### 1. `production.py`
- Production-ready Flask application
- Optimized for Render environment
- Includes health check endpoint
- Better error handling and logging

### 2. `Dockerfile`
- Multi-stage build for smaller image
- Includes FFmpeg for video processing
- Security best practices (non-root user)
- Health check configuration

### 3. `render.yaml`
- Render service configuration
- Auto-deployment setup
- Environment variables
- Disk storage for temporary files

### 4. `requirements.txt`
- Production dependencies
- Fixed versions for stability
- Includes Gunicorn for better performance

## Deployment Commands

### Initial Deployment
```bash
# Deploy to Render
render deploy

# Check deployment status
render ps

# View logs
render logs youtube-downloader
```

### Updating the Application
```bash
# Make changes
git add .
git commit -m "Update features"
git push

# Redeploy (auto-deployment will trigger)
render deploy
```

## Monitoring and Maintenance

### Check Application Status
```bash
# Check service health
curl https://your-app.onrender.com/health

# View logs
render logs youtube-downloader --follow
```

### Common Issues and Solutions

1. **Build Failures**
   - Check Dockerfile syntax
   - Verify requirements.txt versions
   - Review build logs

2. **Runtime Errors**
   - Check application logs
   - Verify environment variables
   - Test health endpoint

3. **Performance Issues**
   - Upgrade to Standard instance
   - Optimize yt-dlp settings
   - Consider Redis for caching

## Custom Domain (Optional)

1. **Add Custom Domain**
   ```bash
   render domains add youtube-downloader.yourdomain.com
   ```

2. **Update DNS**
   - Add CNAME record pointing to `onrender.com`

3. **SSL Certificate**
   - Automatically provisioned by Render

## Scaling Options

### Free Tier (Default)
- 750 hours/month
- Shared CPU
- 512MB RAM
- Sleeps after 15 minutes inactivity

### Standard Tier (Recommended)
- Always on
- Dedicated CPU
- More RAM and storage
- Better performance

## Security Considerations

1. **API Keys**: Store in Render environment variables
2. **Rate Limiting**: Implement in production
3. **HTTPS**: Automatically provided by Render
4. **Input Validation**: Already implemented in the app

## Backup and Recovery

- **Code**: Stored in GitHub
- **Database**: Not used (stateless app)
- **Logs**: Available in Render dashboard
- **Recovery**: Redeploy from GitHub

## Support

- **Render Documentation**: https://render.com/docs
- **Community**: https://community.render.com
- **Status**: https://status.render.com

## Next Steps

1. Deploy using the commands above
2. Test the application at your Render URL
3. Monitor performance and logs
4. Consider upgrading to Standard tier for production use

---

**Note**: This application uses FFmpeg for video processing, which is included in the Dockerfile. The free tier may have performance limitations for large video downloads.
