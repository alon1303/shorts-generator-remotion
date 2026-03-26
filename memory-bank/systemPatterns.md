# System Patterns: Architecture and Design

## System Overview
ShortsGenerator is a modular Python/FastAPI application that converts Reddit stories into short-form videos. The system follows a pipeline architecture where data flows through specialized processing stages.

## High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Input Layer   │───▶│ Processing Layer│───▶│  Output Layer   │
│  - Reddit URLs  │    │  - Story Split  │    │  - Video Files  │
│  - Custom Text  │    │  - TTS Narration│    │  - Subtitles    │
│  - Subreddit    │    │  - Backgrounds  │    │  - Title Cards  │
└─────────────────┘    │  - Subtitles    │    └─────────────────┘
                       │  - Composition  │
                       └─────────────────┘
```

## Core Components

### 1. Input Processing (`reddit_story/`)
- **RedditClient**: Fetches stories from Reddit using public JSON endpoints
- **StoryProcessor**: Splits stories into optimal segments for narration
- **Models**: Data classes (AudioChunk, WordTimestamp, RedditStory)

### 2. Audio Generation (`reddit_story/`)
- **TTS Router**: Routes to different TTS engines (Edge TTS, ElevenLabs)
- **EdgeTTS Client**: Free Microsoft Edge TTS integration
- **AudioMixer**: Mixes narration with sound effects

### 3. Visual Components (`reddit_story/`)
- **BackgroundManager**: Manages background video selection and processing
- **ImageGenerator**: Creates title cards using Playwright HTML-to-image
- **SubtitleGenerator**: Generates ASS format subtitles with word-level highlighting

### 4. Video Composition (`reddit_story/`)
- **VideoComposer**: Main composition engine combining all elements
- **TimingCalculator**: Calculates timing for title card animations

### 5. API Layer (`backend_v2/`)
- **FastAPI Application**: REST API with background job processing
- **Job Management**: In-memory job tracking for async operations
- **Configuration**: Centralized settings management

## Data Flow Patterns

### Primary Pipeline Flow
```
1. Story Acquisition → 2. Text Processing → 3. Audio Generation → 4. Visual Generation → 5. Video Composition
```

### Component Interaction Pattern
```python
# Typical usage pattern
story = await reddit_client.fetch_story(url)
processed = story_processor.process_story(story)
audio_chunks = await tts_router.generate_audio(processed)
video = video_composer.create_video(audio_chunks)
```

## Key Design Patterns

### 1. Pipeline Pattern
Each component processes input and passes output to the next component. Components are loosely coupled and can be tested independently.

### 2. Builder Pattern (VideoComposer)
VideoComposer builds videos step-by-step:
- Creates background clips
- Generates subtitles  
- Combines audio with visuals
- Applies post-processing effects

### 3. Strategy Pattern (TTS Router)
Different TTS engines can be swapped via configuration:
- Edge TTS (default, free)
- ElevenLabs (premium, higher quality)

### 4. Factory Pattern (BackgroundManager)
Creates different types of background clips:
- Single clip from one video
- Sequential clips from multiple videos
- Theme-based selection

### 5. Observer Pattern (Job Tracking)
API endpoints notify clients of processing progress through status updates.

## File Organization Pattern
```
backend_v2/
├── reddit_story/          # Core video generation logic
│   ├── models.py          # Data classes
│   ├── reddit_client.py   # Reddit API
│   ├── story_processor.py # Text processing
│   ├── tts_router.py      # Audio generation
│   ├── background_manager.py # Background videos
│   ├── subtitle_generator.py # Subtitles
│   └── video_composer.py  # Main composition engine
├── config/
│   └── settings.py        # Configuration management
├── main.py               # FastAPI application
├── quick_preview.py      # Quick preview generation tool
└── tests/                # Test files
```

## Configuration Patterns

### Settings Management
- **Centralized Configuration**: All settings in `config/settings.py`
- **Environment Variable Support**: `.env` file loading via pydantic-settings
- **Validation**: Automatic validation with pydantic
- **Directory Management**: Auto-creates necessary directories

### Configuration Categories
```python
# Application settings
APP_NAME, APP_VERSION, DEBUG

# Server settings  
HOST, PORT, WORKERS

# Reddit settings
DEFAULT_SUBREDDIT, MIN_STORY_SCORE

# TTS settings
TTS_ENGINE, DEFAULT_VOICE_ID

# Video settings
TARGET_WIDTH, TARGET_HEIGHT, VIDEO_CRF

# Story settings
MIN_PART_DURATION, MAX_PART_DURATION
```

## Error Handling Patterns

### Component-Level Errors
Each component raises specific exceptions:
- `FileNotFoundError`: Missing required files
- `ValueError`: Invalid parameters
- `RuntimeError`: Processing failures
- `HTTPException`: API errors

### Error Recovery
1. **Validation First**: Validate inputs before processing
2. **Graceful Degradation**: Continue with available components when possible
3. **Cleanup**: Proper cleanup of temporary files on failure
4. **Logging**: Detailed logging for debugging

## Concurrency Patterns

### Async Processing
- **FastAPI Async Endpoints**: Non-blocking HTTP handlers
- **Background Tasks**: Long-running operations in background
- **Job Tracking**: In-memory job status tracking

### Sequential vs Parallel
- **Sequential**: Within a single video (background clips, subtitle generation)
- **Parallel**: Multiple videos can be processed concurrently via API

## State Management Patterns

### Stateless Components
Most components are stateless - they process input and produce output without maintaining internal state.

### Cached State
- **Background Metadata**: Video metadata cached to avoid repeated ffprobe calls
- **Job Tracking**: In-memory job status (in production would use Redis/database)

### Temporary State
- **Temporary Files**: Created during processing, cleaned up automatically
- **Intermediate Results**: Passed between components via data classes

## Testing Patterns

### Unit Testing
Each component has corresponding test file:
- `test_video_composer.py`
- `test_background_manager.py`
- `test_reddit_client.py`

### Mock Patterns
- **File Operations**: Mock filesystem for testing
- **External APIs**: Mock HTTP responses
- **FFmpeg**: Mock subprocess calls

### Integration Testing
- **Component Integration**: Test how components work together
- **API Integration**: Test HTTP endpoints
- **End-to-End**: Full pipeline with mocked external dependencies

## Performance Patterns

### Optimization Strategies
1. **Caching**: Metadata caching for background videos
2. **Lazy Loading**: Load resources only when needed
3. **Parallel Processing**: Ready for async video processing
4. **Efficient Encoding**: FFmpeg optimization flags

### Resource Management
- **Temporary Files**: Automatic cleanup
- **Memory Management**: Proper handling of large video files
- **Process Management**: Subprocess timeouts and resource limits

## Extension Patterns

### Adding New TTS Engines
1. Create new client class following TTS interface
2. Register in TTS router
3. Update configuration options

### Adding New Background Themes
1. Add theme directory with video files
2. Update `BACKGROUND_THEMES` in settings
3. BackgroundManager automatically discovers new themes

### Adding New Subtitle Styles
1. Extend SubtitleGenerator class
2. Add new style configuration
3. Integrate with VideoComposer

## Security Patterns

### Input Validation
- **File Uploads**: Validate file types and sizes
- **URL Input**: Validate Reddit URLs
- **Text Input**: Sanitize user-provided text

### Safe File Operations
- **Path Sanitization**: Prevent directory traversal
- **Temporary Files**: Secure temp file creation
- **File Permissions**: Appropriate file permissions

### API Security
- **CORS Configuration**: Restrict to trusted origins
- **Rate Limiting**: Ready for implementation
- **Input Validation**: Pydantic models for all API inputs

## Deployment Patterns

### Development
- **Local Server**: Uvicorn with auto-reload
- **Virtual Environment**: Python venv for dependencies
- **Environment Variables**: `.env` file for configuration

### Production Ready
- **Process Manager**: Ready for Gunicorn/Uvicorn deployment
- **Configuration**: Environment variable based
- **Logging**: Structured logging with levels
- **Health Checks**: `/health` endpoint

### Scalability Considerations
- **Stateless Design**: Horizontal scaling ready
- **Job Queue**: Architecture supports Celery/Redis
- **Storage**: Configurable output directories

## Monitoring Patterns

### Logging Strategy
- **Structured Logging**: JSON format for production
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Component Logging**: Separate loggers per component

### Health Monitoring
- **Health Endpoint**: `/health` for service status
- **System Info**: `/system-info` for component status
- **Job Status**: API for tracking processing jobs

### Performance Monitoring
- **Processing Time**: Log generation times
- **Resource Usage**: Log memory and CPU usage
- **Error Rates**: Track failure rates

## Maintenance Patterns

### Code Organization
- **Modular Structure**: Each component in separate file
- **Clear Interfaces**: Well-defined function signatures
- **Documentation**: Docstrings and type hints

### Configuration Management
- **Version Control**: Settings in version control
- **Environment Specific**: Different settings per environment
- **Validation**: Automatic validation on load

### Update Strategy
- **Backward Compatibility**: Maintain API compatibility
- **Gradual Rollout**: Feature flags for new features
- **Rollback Plan**: Quick rollback capability
