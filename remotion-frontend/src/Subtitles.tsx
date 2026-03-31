import { AbsoluteFill, useCurrentFrame, useVideoConfig, Sequence } from "remotion";
import React from "react";
import { WordTiming } from "./types";
import { createTikTokStyleCaptions } from "@remotion/captions";

export const Subtitles: React.FC<{ words: WordTiming[]; titleDurationFrames: number }> = ({
  words,
  titleDurationFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // FIX THE OVERLAP BUG: Hide everything if Title Card is still active
  if (frame < titleDurationFrames) {
    return null;
  }

  // 1. Map our WordTiming to Remotion's Caption format (Direct Millisecond Mapping)
  const captions: any[] = words.map((w) => ({
    text: w.word + " ", // Trailing space is required by remotion
    startMs: w.startMs,
    endMs: w.endMs,
    timestampMs: w.startMs,
    confidence: 1
  }));

  // 2. Create TikTok style pages
  const { pages } = createTikTokStyleCaptions({
    captions,
    combineTokensWithinMilliseconds: 1200,
  });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      {pages.map((page: any, index: number) => {
        // Calculate frames from precision milliseconds
        const startFrame = Math.floor((page.startMs / 1000) * fps);
        const lastToken = page.tokens[page.tokens.length - 1];
        const endFrame = Math.floor((lastToken.endMs / 1000) * fps);

        // Filter out pages that ended before Title Card finished
        if (endFrame <= titleDurationFrames) {
          return null;
        }

        // Clip start frame to Title Card end
        const actualStartFrame = Math.max(startFrame, titleDurationFrames);
        const durationInFrames = endFrame - actualStartFrame;

        if (durationInFrames <= 0) {
          return null;
        }

        return (
          <Sequence
            key={index}
            from={actualStartFrame}
            durationInFrames={durationInFrames}
          >
            <CaptionPage page={page} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const CaptionPage: React.FC<{ page: any }> = ({ page }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;

  return (
    <div
      style={{
        color: "white",
        fontSize: 80,
        fontFamily: "Arial, sans-serif",
        fontWeight: "bold",
        textShadow: "0px 5px 10px rgba(0,0,0,0.8), 0px 0px 10px rgba(0,0,0,0.5)",
        WebkitTextStroke: "2px black",
        textAlign: "center",
        width: "80%",
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
      }}
    >
      {page.tokens.map((token: any, i: number) => {
        const isActive = currentMs >= token.startMs && currentMs <= token.endMs;
        return (
          <span
            key={i}
            style={{
              color: isActive ? "yellow" : "white",
              transform: isActive ? "scale(1.1)" : "scale(1.0)",
              display: "inline-block",
              margin: "0 10px",
              transition: "transform 0.1s ease",
            }}
          >
            {token.text}
          </span>
        );
      })}
    </div>
  );
};
