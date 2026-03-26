import { AbsoluteFill, Audio, Sequence, useVideoConfig, staticFile } from "remotion";
import { RemotionInputProps } from "./types";
import { BackgroundLayer } from "./BackgroundLayer";
import { SubtitleLayer } from "./SubtitleLayer";
import { TitleCard } from "./TitleCard";
import React from "react";

export const Main: React.FC<RemotionInputProps> = ({
  audioChunks,
  title,
  author,
  subreddit,
  titleCardDuration,
  backgroundMusicPath,
  backgroundMusicVolume = 0.2,
}) => {
  const { fps } = useVideoConfig();

  // We assume audioChunks[0] is the title narration
  // We'll prepare background clips from all chunks
  let currentStartSeconds = 0;
  const backgroundClips = audioChunks.map((chunk) => {
    const clip = {
      path: "placeholder", // In reality, we'd pass actual background paths
      startInSeconds: currentStartSeconds,
      durationInSeconds: chunk.duration,
    };
    currentStartSeconds += chunk.duration;
    return clip;
  });

  let elapsedSeconds = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {/* Background layer */}
      <BackgroundLayer clips={[]} /> {/* Placeholder for now, real clips will be passed */}

      {/* Title Card layer */}
      <Sequence durationInFrames={Math.round(titleCardDuration * fps)}>
        <TitleCard title={title} author={author} subreddit={subreddit} />
      </Sequence>

      {/* Audio and Subtitles sequencing */}
      {audioChunks.map((chunk, index) => {
        const fromFrame = Math.round(elapsedSeconds * fps);
        const durationFrames = Math.round(chunk.duration * fps);
        
        const chunkElement = (
          <Sequence key={index} from={fromFrame} durationInFrames={durationFrames}>
            <Audio src={staticFile(chunk.audioPath)} />
            <SubtitleLayer wordTimestamps={chunk.wordTimestamps} />
          </Sequence>
        );

        elapsedSeconds += chunk.duration;
        return chunkElement;
      })}

      {backgroundMusicPath && (
        <Audio src={staticFile(backgroundMusicPath)} volume={backgroundMusicVolume} loop />
      )}
    </AbsoluteFill>
  );
};
