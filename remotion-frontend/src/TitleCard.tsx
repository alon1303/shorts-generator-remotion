import { Img, Sequence, staticFile, useVideoConfig, spring, useCurrentFrame } from "remotion";
import React from "react";

export const TitleCard: React.FC<{ asset: string }> = ({ asset }) => {
  const duration = 150; // We'll show title card for 5 seconds
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // A simple spring pop-in
  const popIn = spring({
    frame,
    fps,
    config: { damping: 12 },
  });

  return (
    <Sequence from={0} durationInFrames={duration}>
      <div
        style={{
          position: "absolute",
          top: "15%",
          width: "100%",
          display: "flex",
          justifyContent: "center",
          transform: `scale(${popIn})`,
        }}
      >
        <Img
          src={staticFile(`current_render/${asset}`)}
          style={{
            width: "80%",
            borderRadius: 20,
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
          }}
        />
      </div>
    </Sequence>
  );
};
