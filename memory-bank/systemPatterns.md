# System Patterns: Architecture and Design

## System Overview
ShortsGenerator employs a decoupled architecture separating data generation from video rendering. A Python backend prepares the story, audio, and metadata, while a Remotion (React/TypeScript) frontend handles the actual video composition and rendering.

## High-Level Architecture
```
┌─────────────────────────┐       ┌─────────────────────────┐
│  Python Backend Layer   │       │ Remotion Frontend Layer │
│  (Asset & Data Gen)     │       │ (Video Composition)     │
│                         │       │                         │
│ - Fetch Reddit Story    │ JSON  │ - Parse Data Contract   │
│ - Generate TTS Audio    │ Contract│ - Render Title Card   │
│ - Create Title Card PNG ├───────▶ - Sync Audio & Subtitles│
│ - Select Background MP4 │       │ - Apply Animations      │
│ - Calculate Timestamps  │       │ - Export MP4 Output     │
└─────────────────────────┘       └─────────────────────────┘
```

## The Data Contract (Core Interface)
The sole bridge between the Backend and Frontend is a dedicated output folder per project containing exactly:
1. `audio.mp3` - The generated TTS narration.
2. `title_card.png` - A static image asset for the story title.
3. `background.mp4` - The selected background video clip.
4. `composition_data.json` - The main data contract.

### `composition_data.json` Rules
- Contains relative paths to the generated assets.
- Contains the text and timing for subtitles.
- **CRITICAL TIMING RULE:** The Python backend MUST convert all word timestamps from seconds to frames (based on 30 FPS) before writing them to the JSON. 
  - Formula: `frame = math.floor(seconds * 30)`

## Core Components

### 1. Backend: Data & Asset Exporter (Python)
- **Reddit/NLP**: Fetches content and splits stories optimally for narration.
- **Audio/TTS**: Generates narration via Edge TTS/ElevenLabs.
- **Asset Generator**: Selects background clips and generates static images (e.g., Title Card via Playwright/HTML).
- **Data Compiler**: Compiles timings, converts seconds to 30fps frames, and writes the `composition_data.json`.
- **Constraint**: *No FFmpeg subprocesses for video composition. No rendering logic.*

### 2. Frontend: Video Renderer (Remotion)
- **Composition Engine**: React components mapping the JSON data to timeline sequences.
- **Audio Sync**: Uses Remotion's `<Audio />` and frame-based math to sync subtitles perfectly.
- **Visual Effects**: CSS animations and Remotion interpolations for transitions and word-level highlighting.
- **Export**: Generates the final `.mp4` using Remotion's rendering CLI/API.

## Data Flow Patterns

### Primary Pipeline Flow
```
1. Python Input (Reddit URL) 
   → 2. Python NLP & TTS (Seconds-based timings) 
   → 3. Python Frame Conversion (Seconds to 30FPS Frames)
   → 4. Python Asset Bundling (Output Folder + JSON Contract)
   → 5. Remotion Render (Reads Folder, Composes UI, Outputs MP4)
```

## Anti-Patterns to Avoid
- **Python FFmpeg Rendering**: Do not use Python to concatenate video, overlay text, or render final outputs. 
- **Seconds-Based Frontend Sync**: Do not send raw seconds to the Remotion frontend for word timings. All timestamps must be strictly pre-calculated as frames in the backend.
- **Tight Coupling**: The frontend should not know how data is fetched; the backend should not know how UI is animated. They only share the `composition_data.json` contract.