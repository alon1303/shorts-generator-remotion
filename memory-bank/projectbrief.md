# Project Brief: ShortsGenerator Video Generation

## Overview
ShortsGenerator is a decoupled content creation system that automatically converts Reddit stories into engaging short-form videos (Shorts) for platforms like YouTube, TikTok, and Instagram Reels. The system is split into two distinct layers: a Python backend acting as a Data Exporter, and a Remotion (React/TS) frontend acting as the Video Renderer.

## Core Mission
Transform text-based Reddit content into visually compelling, narrated short videos with professional subtitles, dynamic backgrounds, and audience-retention features using a highly maintainable, modern decoupled architecture.

## Target Users
- Content creators looking to repurpose Reddit stories
- Social media managers automating content production
- Individuals wanting to share stories in video format

## Primary Goals
1. **Automated Pipeline**: Fully automated conversion of Reddit stories to raw assets and data contracts.
2. **Decoupled Architecture**: Strict separation between data preparation (Python) and video rendering (Remotion).
3. **High Quality**: Professional-grade visuals, audio, and subtitles generated precisely via React components.
4. **Scalability**: Efficient processing capable of batch operations without heavy FFmpeg subprocesses hanging the backend.
5. **Platform Optimization**: Videos optimized for 9:16 aspect ratio (1080x1920).

## Architecture Migration Paradigm
The project has moved away from a monolithic Python application heavily reliant on FFmpeg. 
- **Backend (Python)**: Acts strictly as a Data Exporter. Fetches Reddit stories, generates TTS audio, creates static image assets (Title Card), and calculates timing. IT MUST NOT RENDER VIDEO OR USE FFMPEG SUBPROCESSES.
- **Frontend (Remotion)**: Acts as the Video Renderer. Consumes the raw assets and a JSON Data Contract provided by the backend to compose and render the final video.

## Success Metrics
- Zero FFmpeg rendering logic remaining in the Python backend.
- Accurate calculation of word-level timestamps converted to frames (30 FPS) for the UI renderer.
- Seamless generation of the `composition_data.json` contract and required assets (`audio.mp3`, `title_card.png`, `background.mp4`).
- Engaging visual composition with dynamic backgrounds handled purely via web technologies (Remotion).

## Scope Boundaries
### Included
- Reddit story fetching and text NLP processing (Python)
- Text-to-speech narration generation (Python)
- Static visual asset generation like Title Cards (Python)
- JSON Data Contract generation with frame-accurate timestamps (Python)
- Video rendering and UI composition (Remotion/React)

### Excluded
- Python-based video rendering or FFmpeg subprocesses for composition.
- Social media publishing automation (currently)
- Deep learning model training
- Manual video editing interfaces

## Technical Vision
Build a modular, extensible video generation engine using the best tools for each job: Python for data, NLP, and asset generation, and Remotion (React) for perfect, declarative, browser-based video composition and rendering.