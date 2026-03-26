# Technical Context: Technologies and Development Setup

## Technology Stack

### Core Framework
- **Python 3.8+**: Primary programming language
- **FastAPI 0.104.1**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications

### Video Processing
- **FFmpeg**: Command-line video processing tool (external dependency)
- **ffmpeg-python 0.2.0**: Python wrapper for FFmpeg
- **pydub 0.25.1+**: Audio manipulation library

### Text-to-Speech
- **edge-tts 7.0.0+**: Free Microsoft Edge TTS integration
- **ElevenLabs API**: Premium TTS service (optional, requires API key)

### Web and HTML Processing
- **Playwright 1.40.0+**: Browser automation for title card generation
- **Jinja2 3.1.0+**: Templating engine for HTML generation
- **html2image 2.0.3+**: HTML to image conversion (legacy, being replaced by Playwright)

### Data Processing and Utilities
- **pydantic 2.12.0+**: Data validation and settings management
- **pydantic-settings 2.12.0+**: Settings management with environment variables
- **python-dotenv 1.2.0+**: Environment variable loading
- **aiofiles 23.0.0+**: Async file operations
- **pysubs2 1.6.0+**: Subtitle file manipulation

### Testing and Development
- **pytest**: Testing framework (implicit)
- **playwright**: Browser automation for testing
- **faster-whisper 1.2.1**: Whisper transcription (for future expansion)

## Development Environment Setup

### Prerequisites
1. **Python 3.8+**: Available on PATH
2. **FFmpeg**: Installed and available on PATH
3. **Git**: Version control
4. **PowerShell**: Recommended terminal on Windows
5. **Visual Studio Code**: Recommended IDE with Python extension

### Installation Steps
```powershell
# Clone repository (if not already)
git clone <repository-url>
cd sg_video_dev

# Create and activate virtual environment (Windows)
python -m venv backend_v2/venv
backend_v2/venv\Scripts\activate

# Install dependencies
cd backend_v2
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Environment Configuration
1. Copy `.env.example` to `.env` in `backend_v2/` directory
2. Configure any required environment variables (ElevenLabs API key optional)
3. Default settings work without configuration for basic functionality

## System Dependencies

### FFmpeg Installation
**Windows (Chocolatey):**
```powershell
choco install ffmpeg
```

**Windows (Manual):**
1. Download from https://ffmpeg.org/download.html
2. Extract to a directory (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to PATH

**Verification:**
```powershell
ffmpeg -version
```

### Playwright Installation
```powershell
# Install Playwright Python package (included in requirements)
pip install playwright

# Install browser binaries
playwright install chromium
```

## Project Structure

### Key Directories
```
sg_video_dev/
├── backend_v2/                    # Main application
│   ├── config/                    # Configuration
│   │   └── settings.py           # Settings management
│   ├── reddit_story/             # Core video generation
│   │   ├── models.py             # Data models
│   │   ├── reddit_client.py      # Reddit API client
│   │   ├── story_processor.py    # Text processing
│   │   ├── tts_router.py         # TTS engine router
│   │   ├── background_manager.py # Background video management
│   │   ├── subtitle_generator.py # Subtitle generation
│   │   └── video_composer.py     # Main video composer
│   ├── assets/                   # Static assets
│   │   ├── backgrounds/          # Background videos by theme
│   │   └── sfx/                  # Sound effects
│   ├── cache/                    # Cache directory
│   ├── outputs/                  # Generated video output
│   ├── uploads/                  # Temporary uploads
│   └── main.py                   # FastAPI application
├── memory-bank/                  # Project documentation
└── .clinerules/                  # Cline rules and instructions
```

### Configuration Files
- **`backend_v2/config/settings.py`**: Centralized application settings
- **`backend_v2/.env`**: Environment variables (not in version control)
- **`backend_v2/requirements.txt`**: Python dependencies
- **`.gitignore`**: Git ignore rules

## Development Workflow

### Running the Application
```powershell
# Activate virtual environment
backend_v2\venv\Scripts\activate

# Run development server
cd backend_v2
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or run directly
python main.py
```

### Testing
```powershell
# Run individual test files
python -m pytest backend_v2/test_video_composer.py -v

# Run all tests
python -m pytest backend_v2/ -v

# Run with coverage
python -m pytest backend_v2/ --cov=backend_v2 --cov-report=html
```

### Code Quality
```powershell
# Format code with black
black backend_v2/

# Sort imports with isort
isort backend_v2/

# Type checking with mypy (if configured)
mypy backend_v2/
```

## Technical Constraints

### Performance Constraints
1. **Video Processing**: CPU-intensive; FFmpeg operations can be slow
2. **Memory Usage**: Video processing requires significant RAM (500MB+)
3. **Disk I/O**: Temporary files and video assets require fast storage
4. **Network**: TTS and Reddit APIs require internet connectivity

### Platform Constraints
1. **Windows Primary**: Development focused on Windows, but designed to be cross-platform
2. **FFmpeg Dependency**: Must be installed separately
3. **Playwright Browsers**: Requires Chromium installation
4. **Python 3.8+**: Minimum Python version

### Security Constraints
1. **No Authentication**: Current implementation assumes trusted network
2. **File Uploads**: Limited validation on uploaded files
3. **API Keys**: ElevenLabs API key stored in environment variables
4. **Reddit API**: Uses public endpoints only

## Tool Usage Patterns

### FFmpeg Usage Patterns
```python
# Typical FFmpeg command construction
cmd = [
    'ffmpeg',
    '-y',  # Overwrite output
    '-i', input_path,
    '-filter_complex', filter_string,
    '-c:v', 'libx264',
    '-preset', 'veryfast',
    '-crf', '23',
    output_path
]

# Common operations:
# 1. Extract clip: -ss START -t DURATION
# 2. Crop and scale: crop=W:H:X:Y,scale=W:H
# 3. Concatenate: -f concat -i filelist.txt -c copy
# 4. Add subtitles: subtitles=file.ass
```

### Async Programming Patterns
```python
# FastAPI async endpoints
@app.post("/generate/reddit-story")
async def generate_reddit_story(request: RedditStoryRequest):
    # Async processing
    pass

# Background tasks
background_tasks.add_task(process_reddit_story_background, job_id, request)

# Async file operations
async with aiofiles.open(file_path, 'rb') as f:
    content = await f.read()
```

### Error Handling Patterns
```python
try:
    # Operation that may fail
    result = await some_async_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Configuration Patterns
```python
# Settings loading
from config.settings import settings

# Usage
output_dir = settings.OUTPUT_DIR
target_width = settings.TARGET_WIDTH

# Environment variable override
# Set REDDIT_USER_AGENT in .env or environment
```

## Integration Points

### External APIs
1. **Reddit Public JSON**: No API keys required, uses public endpoints
2. **Edge TTS**: Free Microsoft service, no authentication
3. **ElevenLabs**: Premium service, requires API key
4. **Future**: Social media APIs for direct posting

### File System Integration
1. **Background Videos**: Read from assets/backgrounds/
2. **Cache Storage**: Store TTS audio and metadata
3. **Output Generation**: Write videos to outputs/
4. **Temporary Files**: Create and clean up temp files

### Process Management
1. **Subprocess Management**: FFmpeg process control
2. **Async Task Management**: Background job processing
3. **Resource Cleanup**: Temporary file deletion
4. **Error Recovery**: Process restart and cleanup

## Deployment Considerations

### Development Deployment
- **Local Server**: Uvicorn with auto-reload
- **Virtual Environment**: Isolated Python environment
- **Environment Variables**: Local .env file

### Production Deployment
- **Process Manager**: Gunicorn with Uvicorn workers
- **Reverse Proxy**: Nginx or similar
- **Environment Variables**: System or container environment
- **Logging**: Structured JSON logging
- **Monitoring**: Health checks and metrics

### Containerization (Future)
```dockerfile
# Example Dockerfile structure
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing Strategy

### Unit Tests
- **Component Testing**: Test individual components in isolation
- **Mock External Dependencies**: Mock FFmpeg, TTS, and Reddit APIs
- **Data Validation**: Test data models and validation

### Integration Tests
- **Component Integration**: Test how components work together
- **API Endpoints**: Test HTTP endpoints
- **File Operations**: Test file system interactions

### End-to-End Tests
- **Full Pipeline**: Test complete video generation
- **Error Conditions**: Test failure scenarios
- **Performance Testing**: Test with realistic data sizes

### Test Data Management
- **Test Files**: Create and clean up test files
- **Mock Assets**: Use minimal test assets
- **Isolated Environments**: Each test runs in isolation

## Performance Optimization

### Identified Bottlenecks
1. **FFmpeg Processing**: Video encoding is CPU-intensive
2. **TTS Generation**: Network latency for remote TTS
3. **File I/O**: Reading/writing large video files
4. **Memory Usage**: Video processing buffers

### Optimization Strategies
1. **Parallel Processing**: Process multiple videos concurrently
2. **Caching**: Cache TTS results and video metadata
3. **Efficient Encoding**: Use FFmpeg presets optimized for speed
4. **Memory Management**: Stream processing where possible

### Monitoring Metrics
1. **Processing Time**: Time per video segment
2. **Memory Usage**: Peak memory during processing
3. **CPU Utilization**: FFmpeg CPU usage
4. **Disk I/O**: Read/write throughput

## Troubleshooting Guide

### Common Issues

#### FFmpeg Not Found
```
Error: FileNotFoundError: [WinError 2] The system cannot find the file specified
```
**Solution**: Ensure FFmpeg is installed and in PATH

#### Playwright Browser Issues
```
Error: Browser chromium not found
```
**Solution**: Run `playwright install chromium`

#### TTS Generation Failure
```
Error: edge_tts.CommunicationError: Connection failed
```
**Solution**: Check internet connection and retry

#### Memory Errors
```
Error: MemoryError or slow processing
```
**Solution**: Reduce concurrent processes, increase system RAM

#### Video Output Issues
```
Error: Output file empty or corrupted
```
**Solution**: Check FFmpeg command syntax, verify input files

### Debugging Commands
```powershell
# Check FFmpeg installation
ffmpeg -version

# Check Python environment
python --version
pip list | findstr "fastapi ffmpeg"

# Check Playwright
python -c "import playwright; print(playwright.__version__)"

# Run with debug logging
uvicorn main:app --reload --log-level debug
```

### Log Analysis
- **Application Logs**: Check for error messages and stack traces
- **FFmpeg Logs**: Check stderr output from FFmpeg commands
- **API Logs**: Check FastAPI access and error logs
- **System Logs**: Check system resource usage

## Development Guidelines

### Code Style
- **PEP 8**: Follow Python style guide
- **Type Hints**: Use type annotations for all functions
- **Docstrings**: Include docstrings for all public functions
- **Error Handling**: Use explicit exception handling

### Git Workflow
- **Feature Branches**: Create branches for new features
- **Commit Messages**: Use descriptive commit messages
- **Pull Requests**: Review before merging to main
- **Testing**: Run tests before committing

### Documentation
- **Code Comments**: Explain complex logic
- **API Documentation**: Keep FastAPI endpoint docs updated
- **Memory Bank**: Update after significant changes
- **README**: Keep project README current

### Security Best Practices
- **Input Validation**: Validate all user inputs
- **File Operations**: Sanitize file paths
- **Environment Variables**: Store secrets in .env
- **Dependency Updates**: Keep dependencies updated
