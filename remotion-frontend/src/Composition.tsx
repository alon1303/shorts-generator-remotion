import { AbsoluteFill, Audio, staticFile } from "remotion";
import React from "react";
import { CompositionData } from "./types";
import { Background } from "./Background";
import { TitleCard } from "./TitleCard";
import { Subtitles } from "./Subtitles";

export const MainComposition: React.FC<{ data: CompositionData }> = ({ data }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Background backgrounds={data.backgrounds} />
      <TitleCard data={data.titleCardData} duration={data.metadata.titleDurationFrames} />
      <Subtitles
        words={data.words}
        titleDurationFrames={data.metadata.titleDurationFrames}
      />
      <Audio src={staticFile(`current_render/${data.assets.audio}`)} />
      {data.assets.bg_music && (
        <Audio
          src={staticFile(`current_render/${data.assets.bg_music}`)}
          volume={0.15}
          loop
        />
      )}
    </AbsoluteFill>
  );
};
