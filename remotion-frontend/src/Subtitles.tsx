import { AbsoluteFill, useCurrentFrame } from "remotion";
import React from "react";
import { WordTiming } from "./types";

export const Subtitles: React.FC<{ words: WordTiming[] }> = ({ words }) => {
  const frame = useCurrentFrame();

  // Find the currently spoken word
  const currentWord = words.find((w) => frame >= w.startFrame && frame <= w.endFrame);

  if (!currentWord) return null;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
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
          transform: "scale(1.1)", // Pop out the active word slightly
        }}
      >
        {currentWord.word}
      </div>
    </AbsoluteFill>
  );
};
