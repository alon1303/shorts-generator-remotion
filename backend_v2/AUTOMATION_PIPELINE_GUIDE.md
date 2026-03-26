# ShortsGenerator End-to-End Automation Pipeline

## Overview

This is a complete, production-ready automation pipeline that:
1. **Fetches trending Reddit stories** from multiple subreddits using public JSON endpoints (no API keys required)
2. **Generates Shorts videos** with AI narration, dynamic subtitles, and animated title cards
3. **Uploads to YouTube** with proper metadata, tags, and #shorts formatting
4. **Prevents duplicates** by tracking processed posts
5. **Handles errors gracefully** with retry logic and comprehensive logging

## Architecture

### Core Components

1. **`youtube/uploader.py`** - YouTube Data API v3 integration
   - OAuth2 token management with automatic refresh
   - Upload videos with proper Shorts metadata
   - Generate optimized titles, descriptions, and tags
   - Handle quota limits and network errors

2. **`auto_pipeline.py`** - Orchestration engine
   - Fetches stories from multiple subreddits
   - Processes stories sequentially with retry logic
   - Manages YouTube upload rate limiting
   - Tracks statistics and logs everything
   - Supports both single-cycle and continuous operation

3. **`reddit_story/`** - Existing video generation pipeline
   - `reddit_client.py` - Story fetching with duplicate prevention
   - `story_processor.py` - Text splitting and duration estimation
   - `tts_router.py` - AI narration with word-level timestamps
   - `video_composer.py` - Video creation with subtitles and animations
   - `image_generator_new.py` - Dynamic title card generation

## Installation & Setup

### 1. Install Dependencies

```bash
cd backend_v2
pip install -r requirements.txt
```

### 2. YouTube API Setup

**CRITICAL: You must obtain `client_secrets.json` from Google Cloud Console:**

1. Go to https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable **YouTube Data API v3**
4. Create **OAuth 2.0 credentials** (Desktop application)
5. Download `client_secrets.json` and place it in `backend_v2/`
6. On first run, you'll authenticate via browser to get `token.json`

### 3. Verify Installation

```bash
python test_imports.py
```

This will check all dependencies and configuration.

## Usage

### Quick Start (Test Mode)

Run a single cycle without YouTube upload to verify everything works:

```bash
python auto_pipeline.py --single-cycle --no-upload
```

### Production Usage

Run continuously with YouTube uploads (default: 60-minute intervals):

```bash
python auto_pipeline.py --interval 60
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--subreddits` | Subreddits to fetch from | `AmItheAsshole tifu TrueOffMyChest pettyrevenge EntitledParents` |
| `--stories` | Stories per cycle | `3` |
| `--max-duration` | Max video duration (minutes) | `3` |
| `--theme` | Background theme | `minecraft` |
| `--voice` | TTS voice ID | Default Edge TTS voice |
| `--no-upload` | Disable YouTube upload | `False` |
| `--privacy` | YouTube privacy (`private/public/unlisted`) | `private` |
| `--upload-delay` | Delay between uploads (seconds) | `300` |
| `--interval` | Minutes between cycles | `60` |
| `--cycles` | Maximum number of cycles | Unlimited |
| `--single-cycle` | Run once and exit | `False` |
| `--retries` | Max retries per story | `2` |

## Configuration

### Pipeline Settings (in `auto_pipeline.py` constructor)

```python
pipeline = AutoPipeline(
    subreddits=["AmItheAsshole", "tifu"],  # Subreddits to fetch
    stories_per_run=3,                     # Stories per cycle
    max_video_duration_minutes=3,          # Max video length
    theme="minecraft",                     # Background theme
    voice_id=None,                         # TTS voice (uses default)
    upload_to_youtube=True,                # Enable/disable uploads
    youtube_privacy_status="private",      # private/public/unlisted
    delay_between_uploads_seconds=300,     # 5 minutes between uploads
    max_retries_per_story=2,               # Retry failed stories
    skip_processed_posts=True,             # Duplicate prevention
)
```

### Application Settings (in `config/settings.py`)

- `DEFAULT_BACKGROUND_THEME`: Background theme for videos
- `MIN_STORY_SCORE`: Minimum Reddit score (upvotes) 
- `MIN_STORY_LENGTH`: Minimum story length in characters
- `MAX_STORY_LENGTH`: Maximum story length in characters
- `TTS_ENGINE`: Text-to-speech engine (`edge` only)
- `ENABLE_CACHE`: Enable caching for TTS and images

## Error Handling & Recovery

The pipeline is designed to be resilient:

### 1. **Network Errors**
- Automatic retry with exponential backoff
- Continues to next story if one fails
- Logs all errors with stack traces

### 2. **YouTube Quota Limits**
- Detects quota exceeded errors
- Can be configured to stop or continue
- Waits between uploads to avoid limits

### 3. **Processing Failures**
- Individual story failures don't stop pipeline
- Failed stories are logged for manual review
- Statistics track success/failure rates

### 4. **Duplicate Prevention**
- Tracks processed post IDs in `data/processed_posts.json`
- Prevents re-processing the same story
- Can be disabled with `skip_processed_posts=False`

## Monitoring & Logging

### Log Files
- `outputs/auto_pipeline.log` - Main pipeline log
- `data/pipeline_stats.json` - Statistics and metrics
- `data/pipeline/cycle_*.json` - Individual cycle results

### Statistics Tracked
- Total stories processed
- Success/failure rates
- Average story/video durations
- YouTube quota errors
- Network/processing/upload errors

### Viewing Statistics

```python
from auto_pipeline import AutoPipeline

pipeline = AutoPipeline()
await pipeline.initialize()
pipeline.print_stats()  # Prints summary to console
```

## Production Considerations

### 1. **YouTube API Quota**
- Default quota: 10,000 units/day
- Video upload: ~1,600 units
- **Recommendation:** Limit to 5-6 uploads per day

### 2. **Resource Usage**
- Video generation is CPU/GPU intensive
- Consider running on dedicated server
- Monitor disk space for generated videos

### 3. **Legal & Compliance**
- Adds disclaimer to YouTube descriptions
- Attributes content to original Reddit posts
- Uses publicly available Reddit data
- Consider adding opt-out mechanism

### 4. **Scaling**
- Can run multiple instances with different subreddits
- Increase `stories_per_run` for more throughput
- Adjust `interval_minutes` for frequency

## Troubleshooting

### Common Issues

1. **"No module named 'google.oauth2'"**
   ```bash
   pip install -r requirements.txt
   ```

2. **"client_secrets.json not found"**
   - Obtain from Google Cloud Console
   - Place in `backend_v2/` directory

3. **YouTube authentication fails**
   - Delete `youtube/token.json`
   - Re-run to trigger OAuth flow
   - Ensure browser is available for first auth

4. **Video generation fails**
   - Check FFmpeg is installed: `ffmpeg -version`
   - Verify disk space in `outputs/` directory
   - Check logs for specific error messages

5. **No stories fetched**
   - Check internet connection
   - Verify subreddit names are correct
   - Adjust `MIN_STORY_SCORE` in settings

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Example Workflows

### Daily Batch Processing

```bash
# Run at 9 AM daily, process 5 stories, upload to YouTube
python auto_pipeline.py \
  --stories 5 \
  --interval 1440 \
  --privacy unlisted \
  --upload-delay 600
```

### Testing New Subreddits

```bash
# Test new subreddits without YouTube upload
python auto_pipeline.py \
  --subreddits Relationships LifeProTips \
  --single-cycle \
  --no-upload
```

### High-Volume Processing

```bash
# Process many stories, save videos locally
python auto_pipeline.py \
  --stories 10 \
  --no-upload \
  --interval 30 \
  --cycles 48  # Run for 24 hours
```

## Support & Maintenance

### Regular Maintenance Tasks

1. **Clear old videos:** Periodically clean `outputs/reddit_stories/`
2. **Backup statistics:** Backup `data/pipeline_stats.json`
3. **Monitor logs:** Check `outputs/auto_pipeline.log` for errors
4. **Update dependencies:** Periodically update `requirements.txt`

### Getting Help

- Check logs for error messages
- Verify all dependencies are installed
- Ensure YouTube API is enabled
- Confirm `client_secrets.json` is valid

## License & Attribution

This pipeline:
- Uses Reddit's public JSON endpoints
- Adds attribution to original posts
- Includes disclaimer in video descriptions
- Is for educational/automation purposes

**Always respect content creators and platform terms of service.**

---

**Next Steps:**
1. Obtain `client_secrets.json` from Google Cloud Console
2. Run `python test_imports.py` to verify installation
3. Test with `python auto_pipeline.py --single-cycle --no-upload`
4. Authenticate YouTube with `python -m youtube.uploader`
5. Run production pipeline: `python auto_pipeline.py --interval 60`