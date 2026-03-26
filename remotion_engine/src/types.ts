export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

export interface BackgroundClip {
  path: string;
  duration: number;
}

export interface AudioChunk {
  audioPath: string;
  text: string;
  duration: number;
  wordTimestamps: WordTimestamp[];
}

export interface RemotionInputProps {
  audioChunks: AudioChunk[];
  title: string;
  author: string;
  subreddit: string;
  titleCardDuration: number;
  backgroundMusicPath?: string;
  backgroundMusicVolume?: number;
  fps?: number;
  width?: number;
  height?: number;
}
