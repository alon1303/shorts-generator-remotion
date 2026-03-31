import "./index.css";
import { Composition } from "remotion";
import { MainComposition } from "./Composition";
import { CompositionData } from "./types";
import compositionData from "./composition_data.json";

export const RemotionRoot: React.FC = () => {
  const data = compositionData as CompositionData;
  console.log(data);
  
  return (
    <>
      <Composition
        id="RedditShort"
        component={MainComposition}
        durationInFrames={data.metadata.duration_frames || 600}
        fps={data.metadata.fps || 30}
        width={1080}
        height={1920}
        defaultProps={{
          data
        }}
      />
    </>
  );
};
