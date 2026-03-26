import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import React from "react";
import { WordTimestamp } from "./types";

interface SubtitleLayerProps {
  wordTimestamps: WordTimestamp[];
}

export const SubtitleLayer: React.FC<SubtitleLayerProps> = ({ wordTimestamps }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Find the active word
  const activeWordIndex = wordTimestamps.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  if (activeWordIndex === -1) return null;

  // We show a small window of words around the active one (Hormozi style)
  const windowSize = 3;
  const startIdx = Math.max(0, activeWordIndex - Math.floor(windowSize / 2));
  const endIdx = Math.min(wordTimestamps.length, startIdx + windowSize);
  const visibleWords = wordTimestamps.slice(startIdx, endIdx);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        top: "70%",
        height: "20%",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "15px",
          padding: "20px",
        }}
      >
        {visibleWords.map((word, i) => {
          const isActive = word === wordTimestamps[activeWordIndex];
          const scale = isActive ? interpolate(frame % 5, [0, 2.5, 5], [1, 1.1, 1]) : 1;
          
          return (
            <span
              key={`${word.word}-${i}`}
              style={{
                color: isActive ? "#FFFF00" : "white",
                fontSize: "70px",
                fontWeight: "900",
                textTransform: "uppercase",
                textShadow: "4px 4px 0px rgba(0,0,0,1)",
                fontFamily: "Arial Black, sans-serif",
                transform: `scale(${scale})`,
                transition: "transform 0.1s ease-out",
              }}
            >
              {word.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
