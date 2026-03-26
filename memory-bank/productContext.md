# Product Context: Why ShortsGenerator Exists

## Problem Statement
Content creators face significant challenges repurposing text-based content (like Reddit stories) into engaging short-form video content. Manual video creation is time-consuming, requiring skills in video editing, audio production, and graphic design that many creators lack.

## Market Opportunity
Short-form video platforms (YouTube Shorts, TikTok, Instagram Reels) are experiencing explosive growth, with algorithms favoring consistent, high-quality content. However, producing daily videos manually is unsustainable for most creators.

## Solution Overview
ShortsGenerator automates the entire process of converting Reddit stories into professional short-form videos by:

1. **Fetching Content**: Automatically retrieves trending Reddit stories
2. **Generating Narration**: Converts text to high-quality speech using TTS
3. **Creating Visuals**: Adds dynamic backgrounds and professional subtitles
4. **Optimizing Format**: Formats videos specifically for 9:16 short-form platforms

## User Experience Goals
### For Content Creators
- **Time Savings**: Reduce video creation from hours to minutes
- **Consistent Quality**: Professional output every time
- **Scalability**: Batch process multiple stories simultaneously
- **Customization**: Adjust themes, voices, and styles to match brand

### For Viewers
- **Engaging Content**: Professional videos that hold attention
- **Accessibility**: Subtitles make content consumable in any environment
- **Pacing**: Strategic CTAs and segmentation maintain interest

## Key Differentiators
1. **Word-Level Subtitle Sync**: Not just line-by-line, but word-by-word highlighting (Hormozi style)
2. **Dynamic Background Sequencing**: Multiple background clips per video for visual variety
3. **Strategic CTAs**: Automated audience retention techniques built into narration
4. **No API Keys Required**: Uses public Reddit endpoints and free TTS services
5. **Post-Specific Organization**: Creates organized folders with title cards for each story

## How It Should Work
### Ideal Workflow
1. User provides Reddit URL or selects subreddit
2. System fetches story, analyzes text, splits into optimal segments
3. Generates title card with Reddit post styling
4. Creates narration with strategic CTAs for retention
5. Combines audio with dynamic backgrounds and subtitles
6. Outputs organized video files ready for upload

### Quality Standards
- **Audio**: Clear, natural-sounding narration with proper pacing
- **Visuals**: High-quality 1080x1920 resolution, engaging backgrounds
- **Subtitles**: Perfect timing with word-level highlighting
- **Structure**: Logical segmentation with smooth transitions
- **Performance**: Videos load quickly and play smoothly on mobile devices

## Business Impact
### For Individual Creators
- Increased posting frequency without increased effort
- Higher engagement through professional presentation
- Ability to test multiple content styles quickly

### For Agencies/Teams
- Consistent branding across multiple creators
- Scalable content production pipeline
- Reduced dependency on specialized video editors

## Future Vision
### Phase 1: Core Pipeline ✓
- Basic Reddit-to-video conversion
- Edge TTS integration
- Simple background management

### Phase 2: Enhanced Features
- Multiple TTS engine support (ElevenLabs, etc.)
- Advanced subtitle animations
- AI-generated background imagery
- Template system for different video styles

### Phase 3: Platform Expansion
- Integration with social media APIs for direct posting
- Analytics and performance tracking
- Community template sharing
- Marketplace for voice actors/backgrounds

## Success Indicators
- Users can generate their first video within 5 minutes of setup
- Generated videos achieve comparable engagement to manually created content
- System processes at least 10 videos per hour on standard hardware
- Users report 80%+ time savings compared to manual creation
- Generated videos pass platform quality checks (no compression artifacts, clear audio)
