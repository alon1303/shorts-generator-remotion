import { AbsoluteFill, Video, useVideoConfig } from "remotion";
import React from "react";

export interface BackgroundClip {
  path: string;
  startInSeconds: number;
  durationInSeconds: number;
}

interface BackgroundLayerProps {
  clips: BackgroundClip[];
}

export const BackgroundLayer: React.FC<BackgroundLayerProps> = ({ clips }) => {
  const { fps } = useVideoConfig();

  if (!clips || clips.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: "#222" }} />;
  }

  return (
    <AbsoluteFill>
      {clips.map((clip, index) => {
        const startFrame = Math.round(clip.startInSeconds * fps);
        const durationFrames = Math.round(clip.durationInSeconds * fps);
        
        return (
          <Video
            key={`${clip.path}-${index}`}
            src={clip.path}
            startFrom={0} // This assumes the clips are already cut, or we can add startFrom if needed
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
            // We use standard React conditional rendering or AbsoluteFill with sequences
            // But Remotion's <Video> can be placed inside Sequences in the parent
          />
        );
      })}
    </AbsoluteFill>
  );
};
