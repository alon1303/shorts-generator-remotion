# Technical Context: Technologies and Development Setup

## Technology Stack

### Backend Data Exporter (Python)
- **Python 3.8+**: Core language for data extraction and processing.
- **FastAPI**: API framework for kicking off jobs and serving asset generation requests.
- **Edge-TTS / ElevenLabs**: Text-to-Speech engines for generating narration.
- **Pydantic**: For strict enforcement of the `composition_data.json` schema.
- **(DEPRECATED) Playwright**: NO LONGER used for title cards. The Title Card is now a native React component in Remotion.

### Frontend Video Renderer (Remotion)
- **Remotion**: React-based framework for creating videos programmatically.
- **React & TypeScript**: UI definition, state management, and type-safe data parsing.
- **Tailwind CSS**: For styling subtitle components and title card overlays.

## Architectural Paradigm Shift

### Deprecated Technologies
- **FFmpeg (via subprocess or ffmpeg-python)**: **REMOVED** from the Python pipeline for final video composition.
- **Playwright / html2image**: **REMOVED** for title card generation. Remotion renders the title card natively using React.
- **pysubs2**: **REMOVED** as Remotion now handles all subtitle rendering natively in the browser/React layer.

### New Division of Labor
1. **Python** handles heavily I/O bound tasks and complex logic: network requests, TTS generation, NLP/word timing extraction, and building the frame-accurate JSON contract.
2. **Remotion** handles ALL visual composition: timeline sequencing, CSS animations, subtitle highlighting, and video encoding.

## Data Contract Definition (`composition_data.json`)

The Python backend is responsible for creating the asset bundle. 
**Example directory structure (Handoff Location):**
`remotion-frontend/public/current_render/`
```
audio.mp3
bg_music.mp3
backgrounds/
  bg1.mp4
  bg2.mp4
composition_data.json
```

**Crucial Timing Logic (Python side):**
Remotion operates on strict frame counts. Python must calculate word-level and background timestamps using a base of 30 Frames Per Second (FPS).
```python
FPS = 30
# Background Timing (Example)
bg_start_frame = int(bg_start_seconds * FPS)
bg_end_frame = int(bg_end_seconds * FPS)

# Word Timing (Example)
word_start_frame = int(word_start_seconds * FPS)
word_end_frame = int(word_end_seconds * FPS)
```

## Development Environment Setup

### Backend (Python)
```powershell
python -m venv backend_v2/venv
backend_v2/venv\Scripts\activate
pip install -r backend_v2/requirements.txt
```

### Frontend (Remotion)
Requires Node.js 18+ and npm/yarn/pnpm.

## Integration Points
1. **Asset Generation:** Python scripts compile the asset bundle (audio, music, backgrounds, and JSON).
2. **THE HANDOFF:** The backend copies all assets into `remotion-frontend/public/current_render`. This is the single source of truth for the active render.
3. **Remotion Render:** The Remotion CLI/Player consumes the data in `current_render` to compose the UI and output the final `.mp4`.
