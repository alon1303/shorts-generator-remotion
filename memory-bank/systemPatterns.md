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
│ - Generate TTS Audio    │ Contract│ - Native React Title Card│
│ - Calc Timing Frames    ├───────▶ - Sync Audio & Subtitles│
│ - Select Background MP4 │       │ - Apply Animations      │
│ - Calculate Timestamps  │       │ - Export MP4 Output     │
└─────────────────────────┘       └─────────────────────────┘
```

## THE NEW DATA CONTRACT (`composition_data.json`)
The bridge between the Backend and Frontend is the `composition_data.json` file. It MUST strictly adhere to this format:

```json
{
  "assets": {
    "audio": "audio.mp3",
    "bg_music": "lofi_bg.mp3"
  },
  "metadata": {
    "title": "...",
    "subreddit": "...",
    "fps": 30,
    "duration_frames": 1000,
    "titleDurationFrames": 150
  },
  "titleCardData": {
    "titleText": "...",
    "subreddit": "...",
    "author": "...",
    "upvotes": "...",
    "keywords": ["...", "..."]
  },
  "backgrounds": [
    {
      "startFrame": 0,
      "endFrame": 450,
      "backgroundPath": "bg1.mp4"
    },
    {
      "startFrame": 450,
      "endFrame": 900,
      "backgroundPath": "bg2.mp4"
    }
  ],
  "words": [
    {
      "text": "Hello",
      "start": 0,
      "end": 10,
      "highlight": false
    }
  ]
}
```

### Data Contract Rules
- **CRITICAL TIMING RULE:** The Python backend MUST convert all word timestamps from seconds to frames (based on 30 FPS) before writing them to the JSON. Formula: `frame = math.floor(seconds * 30)`.
- **Title Duration:** `metadata.titleDurationFrames` must be the exact frame count where the title TTS ends, plus any desired buffer.
- **Background Sequencing:** `backgrounds` is an array of objects defining start/end frames for each clip.
- **Word Sync:** If silences are stripped from TTS audio, word timestamps MUST be mathematically adjusted to maintain sync.

## STRICT BACKEND RESPONSIBILITIES
- **Data Export:** Fetch content, generate TTS audio, and extract metadata.
- **Timing Calculation:** Accurately calculate `titleDurationFrames` based on TTS timestamps.
- **Background Logic:** Dynamically build the `backgrounds` array (10-15s chunks covering total duration). There is no difference in background logic for regular stories vs "Parts".
- **Timestamp Adjustment:** If TTS silences are removed, word timestamps MUST be updated to match the shortened audio.
- **THE HANDOFF MECHANISM:** The absolute final step before executing Remotion is copying ALL generated assets (`audio.mp3`, `backgrounds`, `bg_music.mp3`, `composition_data.json`) into `remotion-frontend/public/current_render`.
- **Constraint:** *No FFmpeg subprocesses for final video composition. The backend only prepares raw assets.*

## STRICT FRONTEND RESPONSIBILITIES
- **Type Safety (`types.ts`):** Must perfectly reflect the updated JSON contract (add `BackgroundTiming` interface, add `titleDurationFrames`, update `assets`).
- **Composition Logic (`Composition.tsx`):** Passes `metadata.titleDurationFrames` to `<TitleCard />` and the `backgrounds` array to `<Background />`.
- **Dynamic Title Card (`TitleCard.tsx`):** MUST accept `duration` as a prop (no hardcoding) and use it dynamically for the Sequence and exit animations.
- **Multi-Sequence Background (`Background.tsx`):** Must map over the `backgrounds` array and render multiple `<Sequence>` components, each containing a `<Video>`.

## Core Components

### 1. Backend: Data & Asset Exporter (Python)
- **Reddit/NLP**: Fetches content and splits stories optimally for narration.
- **Audio/TTS**: Generates narration via Edge TTS/ElevenLabs.
- **Asset Selection**: Chooses background clips and populates the timing array.
- **Data Compiler**: Compiles timings, converts seconds to 30fps frames, and writes the `composition_data.json`.

### 2. Frontend: Video Renderer (Remotion)
- **Composition Engine**: React components mapping the JSON data to timeline sequences.
- **Audio Sync**: Uses Remotion's `<Audio />` and frame-based math to sync subtitles perfectly.
- **Visual Effects**: CSS animations and Remotion interpolations for transitions and word-level highlighting.
- **Export**: Generates the final `.mp4` using Remotion's rendering CLI.

## Anti-Patterns to Avoid
- **Python FFmpeg Rendering**: Do not use Python to concatenate video, overlay text, or render final outputs. 
- **Seconds-Based Frontend Sync**: Do not send raw seconds to the Remotion frontend for word timings. All timestamps must be strictly pre-calculated as frames in the backend.
- **Hardcoded Frontend Durations**: All sequence lengths and animation timings should be derived from the Data Contract.
- **Tight Coupling**: The frontend should not know how data is fetched; the backend should not know how UI is animated. They only share the `composition_data.json` contract.