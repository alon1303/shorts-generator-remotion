export type WordTiming = {
  word: string;
  startFrame: number;
  endFrame: number;
};

export type TitleCardData = {
  titleText: string;
  subreddit: string;
  author: string;
  upvotes: string;
  keywords: string[];
};

export type CompositionData = {
  assets: {
    audio: string;
    background: string;
  };
  metadata: {
    title: string;
    subreddit: string;
    fps: number;
    duration_frames: number;
  };
  titleCardData: TitleCardData;
  words: WordTiming[];
};
