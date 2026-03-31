import { AbsoluteFill } from "remotion";
import React from "react";
import { CompositionData } from "./types";
import { Background } from "./Background";
import { TitleCard } from "./TitleCard";
import { Subtitles } from "./Subtitles";

export const MainComposition: React.FC<{ data: CompositionData }> = ({ data }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Background assets={data.assets} />
      <TitleCard data={data.titleCardData} />
      <Subtitles words={data.words} />
    </AbsoluteFill>
  );
};
