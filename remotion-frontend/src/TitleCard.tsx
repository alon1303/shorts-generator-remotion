import { Sequence, useVideoConfig, spring, useCurrentFrame, interpolate } from "remotion";
import React from "react";
import { TitleCardData } from "./types";

export const TitleCard: React.FC<{ data: TitleCardData; duration: number }> = ({ data, duration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance animation (0 to 1 over 18 frames = 0.6s at 30fps)
  const entrance = spring({
    frame,
    fps,
    config: {
      damping: 12,
      mass: 0.5,
      stiffness: 100,
    },
    durationInFrames: 18,
  });

  // Exit animation (starts at duration - 24 frames = 0.8s before end)
  const exit = spring({
    frame: frame - (duration - 24),
    fps,
    config: {
      damping: 12,
      mass: 0.5,
      stiffness: 100,
    },
    durationInFrames: 24,
  });

  const scale = interpolate(entrance, [0, 1], [0.8, 1]) * interpolate(exit, [0, 1], [1, 0.9]);
  const opacity = entrance * (1 - exit);

  const renderTitle = (text: string, keywords: string[]) => {
    if (!keywords || keywords.length === 0) return text;

    const words = text.split(" ");
    return words.map((word, i) => {
      const cleanWord = word.replace(/[^\w]/g, "").toUpperCase();
      const isKeyword = keywords.some(k => k.toUpperCase() === cleanWord);
      
      return (
        <span key={i} style={{ color: isKeyword ? "#ff4500" : "white" }}>
          {word}{" "}
        </span>
      );
    });
  };

  return (
    <Sequence from={0} durationInFrames={duration}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity,
          transform: `scale(${scale})`,
        }}
      >
        <div
          style={{
            width: "90%",
            backgroundColor: "#1a1a1b", // Reddit dark mode gray
            borderRadius: 12,
            padding: "24px",
            boxShadow: "0 4px 20px rgba(0,0,0,0.6)",
            fontFamily: "IBM Plex Sans, Arial, sans-serif",
            border: "1px solid #343536",
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginBottom: "12px",
            }}
          >
            {/* Subreddit Icon Mock */}
            <div
              style={{
                width: "24px",
                height: "24px",
                backgroundColor: "#ff4500",
                borderRadius: "50%",
              }}
            />
            <span style={{ color: "#D7DADC", fontWeight: 700, fontSize: "14px" }}>
              {data.subreddit}
            </span>
            <span style={{ color: "#818384", fontSize: "12px" }}>
              • Posted by {data.author} • 5h
            </span>
          </div>

          {/* Title */}
          <h1
            style={{
              color: "#D7DADC",
              fontSize: "28px",
              fontWeight: 600,
              lineHeight: "34px",
              margin: "0 0 16px 0",
              wordWrap: "break-word",
            }}
          >
            {renderTitle(data.titleText, data.keywords)}
          </h1>

          {/* Footer */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                backgroundColor: "#272729",
                padding: "4px 8px",
                borderRadius: "4px",
                gap: "8px",
              }}
            >
              <span style={{ color: "#818384", fontWeight: 700 }}>↑</span>
              <span style={{ color: "#D7DADC", fontWeight: 700, fontSize: "12px" }}>
                {data.upvotes}
              </span>
              <span style={{ color: "#818384", fontWeight: 700 }}>↓</span>
            </div>
            
            <div
              style={{
                display: "flex",
                alignItems: "center",
                backgroundColor: "#272729",
                padding: "4px 8px",
                borderRadius: "4px",
                gap: "6px",
              }}
            >
              <span style={{ color: "#818384", fontSize: "16px" }}>💬</span>
              <span style={{ color: "#818384", fontWeight: 700, fontSize: "12px" }}>
                452 Comments
              </span>
            </div>
          </div>
        </div>
      </div>
    </Sequence>
  );
};
