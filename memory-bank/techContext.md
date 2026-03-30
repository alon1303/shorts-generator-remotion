# Technical Context: Technologies and Development Setup

## Technology Stack

### Backend Data Exporter (Python)
- **Python 3.8+**: Core language for data extraction and processing.
- **FastAPI**: API framework for kicking off jobs and serving asset generation requests.
- **Edge-TTS / ElevenLabs**: Text-to-Speech engines for generating narration.
- **Playwright**: Used to generate static visual assets (like `title_card.png`).
- **Pydantic**: For strict enforcement of the `composition_data.json` schema.

### Frontend Video Renderer (Remotion)
- **Remotion**: React-based framework for creating videos programmatically.
- **React & TypeScript**: UI definition, state management, and type-safe data parsing.
- **CSS / Tailwind** (Optional): For styling subtitle components and title card overlays.

## Architectural Paradigm Shift

### Deprecated Technologies
- **FFmpeg (via subprocess or ffmpeg-python)**: **REMOVED** from the Python pipeline for video composition.
- **pysubs2**: **REMOVED** as Remotion now handles all subtitle rendering natively in the browser/React layer.

### New Division of Labor
1. **Python** handles heavily I/O bound tasks and complex logic: network requests, TTS generation, NLP/word timing extraction, and static image rendering.
2. **Remotion** handles highly visual, frame-accurate UI rendering: timeline sequencing, CSS animations, subtitle highlighting, and video encoding (which Remotion does internally via its own bundled FFmpeg logic, completely opaque to Python).

## Data Contract Definition (`composition_data.json`)

The Python backend is responsible for creating a per-project directory. 
Example directory structure:
```
outputs/
  project_12345/
    audio.mp3
    title_card.png
    background.mp4
    composition_data.json
```

**Crucial Timing Logic (Python side):**
Remotion operates on strict frame counts. Python must calculate word-level timestamps using a base of 30 Frames Per Second (FPS).
```python
FPS = 30
word_start_frame = int(word_start_seconds * FPS)
word_end_frame = int(word_end_seconds * FPS)
```

## Development Environment Setup

### Backend (Python)
```powershell
python -m venv backend_v2/venv
backend_v2/venv\Scripts\activate
pip install -r backend_v2/requirements.txt
playwright install chromium
```

### Frontend (Remotion)
*(To be initialized in Phase 1)*
Requires Node.js 18+ and npm/yarn/pnpm.

## Integration Points
1. Python scripts compile the asset folder.
2. A build script or API call triggers the Remotion CLI, pointing it at the generated `composition_data.json`.
3. Remotion outputs the final `.mp4` video.