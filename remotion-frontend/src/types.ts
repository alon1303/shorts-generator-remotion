export type WordTiming = {
  word: string;
  startFrame: number;
  endFrame: number;
};

export type CompositionData = {
  assets: {
    audio: string;
    title_card: string;
    background: string;
  };
  metadata: {
    title: string;
    subreddit: string;
    fps: number;
    duration_frames: number;
  };
  words: WordTiming[];
};
