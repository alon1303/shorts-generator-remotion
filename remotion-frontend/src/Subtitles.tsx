import { AbsoluteFill, useVideoConfig, Sequence, spring, useCurrentFrame, interpolate } from "remotion";
import React from "react";
import { WordTiming } from "./types";

export const Subtitles: React.FC<{ words: WordTiming[]; titleDurationFrames: number }> = ({
  words,
  titleDurationFrames,
}) => {
  const { fps } = useVideoConfig();

  // 1. Safety check for words array
  if (!words || words.length === 0) {
    return null;
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {words.map((word, i) => {
        if (!word || !word.word) return null;

        // Determine the offset based on the word's timing relative to the title card
        const isSingleRun = word.start > (titleDurationFrames / fps);
        const offsetFrames = isSingleRun ? 0 : titleDurationFrames;

        const from = Math.floor(word.start * fps) + offsetFrames;
        const duration = Math.floor((word.end - word.start) * fps);

        // Filter out words that occur DURING the TitleCard
        if (from < titleDurationFrames) {
          return null;
        }

        if (duration <= 0) return null;

        return (
          <Sequence key={i} from={from} durationInFrames={duration}>
            <SubtitleWord text={word.word} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const SubtitleWord: React.FC<{ text: string }> = ({ text }) => {
  // We MUST call hooks at the top level of the component
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Modern "Pop" animation
  const scale = spring({
    frame,
    fps,
    config: {
      damping: 12,
      stiffness: 200,
      mass: 0.5,
    },
  });

  const rotation = interpolate(scale, [0, 1], [-3, 0]);

  return (
    <AbsoluteFill
        style={{
            justifyContent: "center",
            alignItems: "center",
        }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          width: "100%",
          paddingBottom: "200px", // Push word up from the bottom
        }}
      >
        <span
          style={{
            color: "#FFFF00", // Bright Yellow
            fontSize: 160,
            fontFamily: "Arial Black, sans-serif",
            fontWeight: "900",
            textShadow: "0px 10px 30px rgba(0,0,0,1), 0px 0px 20px rgba(0,0,0,0.8)",
            WebkitTextStroke: "6px black",
            transform: `scale(${scale}) rotate(${rotation}deg)`,
            textAlign: "center",
            display: "inline-block",
            lineHeight: "1",
          }}
        >
          {text.toUpperCase()}
        </span>
      </div>
    </AbsoluteFill>
  );
};
