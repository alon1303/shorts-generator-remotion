import { Composition } from "remotion";
import { Main } from "./Main";
import { RemotionInputProps } from "./types";

const defaultProps: RemotionInputProps = {
  audioChunks: [],
  title: "AITA for creating a Remotion engine?",
  author: "u/Cline",
  subreddit: "r/AmITheAsshole",
  titleCardDuration: 4.5,
  fps: 30,
  width: 1080,
  height: 1920,
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ShortVideo"
        component={Main}
        durationInFrames={1800} // This will be calculated dynamically later
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
      />
    </>
  );
};
