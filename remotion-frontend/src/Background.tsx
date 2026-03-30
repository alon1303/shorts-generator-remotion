import { AbsoluteFill, Audio, Video, staticFile } from "remotion";
import React from "react";

export const Background: React.FC<{ assets: { background: string; audio: string } }> = ({ assets }) => {
  return (
    <AbsoluteFill>
      <Video
        src={staticFile(`current_render/${assets.background}`)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
        muted
        loop
      />
      <Audio src={staticFile(`current_render/${assets.audio}`)} />
    </AbsoluteFill>
  );
};
