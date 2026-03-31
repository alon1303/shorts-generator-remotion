import { AbsoluteFill, Video, staticFile, Sequence } from "remotion";
import React from "react";
import { BackgroundTiming } from "./types";

export const Background: React.FC<{ backgrounds: BackgroundTiming[] }> = ({ backgrounds }) => {
  return (
    <AbsoluteFill>
      {backgrounds.map((bg, index) => (
        <Sequence
          key={index}
          from={bg.startFrame}
          // Overlap by 15 frames to prevent black decoding flashes
          durationInFrames={(bg.endFrame - bg.startFrame) + 15}
        >
          <Video
            src={staticFile(`current_render/${bg.backgroundPath}`)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
            muted
          />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
