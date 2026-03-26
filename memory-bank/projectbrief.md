# Project Brief: ShortsGenerator Video Generation

## Overview
ShortsGenerator is a Python/FastAPI backend system that automatically converts Reddit stories into engaging short-form videos (Shorts) for platforms like YouTube, TikTok, and Instagram Reels.

## Core Mission
Transform text-based Reddit content into visually compelling, narrated short videos with professional subtitles, dynamic backgrounds, and audience-retention features.

## Target Users
- Content creators looking to repurpose Reddit stories
- Social media managers automating content production
- Individuals wanting to share stories in video format

## Primary Goals
1. **Automated Pipeline**: Fully automated conversion of Reddit stories to Shorts videos
2. **High Quality**: Professional-grade visuals, audio, and subtitles
3. **Scalability**: Efficient processing capable of batch operations
4. **Customization**: Flexible theming, voice selection, and styling options
5. **Platform Optimization**: Videos optimized for 9:16 aspect ratio (1080x1920)

## Success Metrics
- Video generation time under 5 minutes per story
- Professional audio quality with natural-sounding TTS
- Accurate word-level subtitle synchronization
- Engaging visual composition with dynamic backgrounds
- High audience retention through strategic CTAs and pacing

## Scope Boundaries
### Included
- Reddit story fetching and processing
- Text-to-speech narration generation
- Background video management and sequencing
- Subtitle generation with word-level highlighting
- Video composition and effects
- FastAPI REST API for automation

### Excluded
- Frontend UI development (separate project)
- Social media publishing automation
- Monetization or analytics features
- Deep learning model training
- Manual video editing interfaces

## Project Evolution
Migrated from Remotion/Node.js to Python/FastAPI for better video processing performance and maintainability. Current focus is on core video creation pipeline while maintaining backward compatibility with existing automation workflows.

## Key Stakeholders
- **Content Creators**: Primary users needing fast, high-quality video generation
- **Developers**: Maintaining and extending the video generation engine
- **Video Platform Algorithms**: Target for optimization (YouTube Shorts, TikTok)

## Technical Vision
Build a modular, extensible video generation engine that can adapt to evolving platform requirements while maintaining consistent output quality and processing efficiency.
