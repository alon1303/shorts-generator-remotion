import { AbsoluteFill, useVideoConfig, spring, interpolate } from "remotion";
import { useCurrentFrame } from "remotion";
import React from "react";

interface TitleCardProps {
  title: string;
  subreddit: string;
  author: string;
}

export const TitleCard: React.FC<TitleCardProps> = ({ title, subreddit, author }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame,
    fps,
    config: {
      damping: 12,
    },
  });

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        zIndex: 10,
      }}
    >
      <div
        style={{
          backgroundColor: "#1A1A1B",
          padding: "30px",
          borderRadius: "10px",
          width: "90%",
          boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
          border: "1px solid #343536",
          opacity: opacity,
          transform: `scale(${entrance})`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", marginBottom: "15px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              backgroundColor: "#FF4500",
              borderRadius: "50%",
              marginRight: "10px",
            }}
          />
          <div>
            <div style={{ color: "white", fontWeight: "bold", fontSize: "24px" }}>
              {subreddit}
            </div>
            <div style={{ color: "#818384", fontSize: "18px" }}>
              Posted by {author}
            </div>
          </div>
        </div>
        <h1
          style={{
            color: "#D7DADC",
            fontSize: "42px",
            lineHeight: "1.2",
            margin: 0,
            fontFamily: "Segoe UI, sans-serif",
          }}
        >
          {title}
        </h1>
      </div>
    </AbsoluteFill>
  );
};
