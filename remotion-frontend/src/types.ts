export type WordTiming = {
  word: string;
  start: number;
  end: number;
};

export type TitleCardData = {
  titleText: string;
  subreddit: string;
  author: string;
  upvotes: string;
  keywords: string[];
};

export type BackgroundTiming = {
  startFrame: number;
  endFrame: number;
  backgroundPath: string;
};

export type CompositionData = {
  assets: {
    audio: string;
    bg_music: string;
  };
  metadata: {
    title: string;
    subreddit: string;
    fps: number;
    duration_frames: number;
    titleDurationFrames: number;
  };
  titleCardData: TitleCardData;
  backgrounds: BackgroundTiming[];
  words: WordTiming[];
};
