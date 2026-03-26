# ShortsGenerator Backend v2

Migration from Remotion/Node.js to Python/FastAPI backend for video processing.

## Architecture Overview

This backend replaces the previous Remotion-based video rendering with a Python/FastAPI solution that uses FFmpeg for efficient video processing.

### Key Changes:
1. **Removed**: Remotion dependency for video rendering
2. **Added**: FastAPI for REST API endpoints
3. **Added**: FFmpeg-based video processing for 16:9 → 9:16 conversion
4. **Added**: Python virtual environment for dependency management

## Project Structure

```
backend_v2/
├── venv/                    # Python virtual environment
├── main.py                 # FastAPI application entry point
├── video_processor.py      # Core video processing module
├── requirements.txt        # Python dependencies
├── uploads/               # Temporary storage for uploaded videos
├── outputs/               # Processed video output directory
└── README.md              # This file
```

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- FFmpeg installed and available in PATH
- Virtual environment support

### 2. Installation

```bash
# Navigate to backend_v2 directory
cd backend_v2

# Create and activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Server

```bash
# Development server with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or run directly
python main.py
```

### 4. API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check endpoint
- `POST /upload/video` - Upload and process video file

## Video Processing Features

### `reframe_to_916(input_path, output_path)`
Converts 16:9 videos to 9:16 (1080x1920) format with smart center cropping.

**Algorithm:**
1. Detect original video dimensions
2. Scale to fit target height (1920px) while maintaining aspect ratio
3. Center crop to exact 1080x1920 dimensions
4. Preserve audio quality by copying without re-encoding
5. Use high-quality encoding settings (CRF 18, slow preset)

**Quality Optimization:**
- Minimal re-encoding where possible
- Audio stream copied without processing
- Hardware acceleration ready (can be extended with NVENC/ProRes)
- Smart scaling to maintain visual quality

## Integration Points

### To be integrated from original backend:
1. **Transcription Service** - Faster-Whisper API for subtitle generation
2. **Subtitle Styling** - .ass subtitle file generation with animations
3. **Face Detection** - OpenCV/Mediapipe for smart reframing
4. **Task Queue** - Celery + Redis for async processing

## Configuration

Environment variables (to be added to `.env`):
```
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
MAX_FILE_SIZE=100MB
ALLOWED_EXTENSIONS=.mp4,.avi,.mkv,.mov,.webm
```

## Testing

```bash
# Test video processing directly
python video_processor.py test_input.mp4 test_output.mp4

# Test API endpoints
curl http://localhost:8000/health
```

## Performance Considerations

1. **FFmpeg Optimization**: Uses efficient filters and minimal re-encoding
2. **Memory Management**: Processes files in chunks for large videos
3. **Parallel Processing**: Ready for Celery integration for batch processing
4. **Quality Settings**: Configurable CRF values for size/quality tradeoff

## Migration Status

✅ **Completed:**
- Basic FastAPI structure
- Video reframing from 16:9 to 9:16
- Virtual environment setup
- API endpoints for video upload

🔧 **Pending Integration:**
- Transcription service (Faster-Whisper)
- Subtitle generation and styling
- Face detection for smart cropping
- Async task processing (Celery + Redis)
- Frontend integration

## Next Steps

1. Integrate transcription service from `ApiService/faster-whisper-api.ts`
2. Add subtitle styling with .ass file generation
3. Implement face detection for intelligent cropping
4. Add Celery for async task processing
5. Update frontend to use new API endpoints