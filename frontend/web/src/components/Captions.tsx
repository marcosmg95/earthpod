import type { LoadedTrack } from "../data/useTrack";
import type { Cue } from "../data/vtt";
import { cueAt, useEngine } from "../engine/store";

/**
 * The description of the moment, shown like film subtitles.
 * Hidden from screen readers: they already hear it as an announcement, and the transcript has it all.
 */
export function Captions({ track }: { track: LoadedTrack }) {
  const { time } = useEngine();
  const cue = track.cues[cueAt(track.cues, time)] as Cue | undefined;
  return (
    <p className="captions" aria-hidden="true">
      {cue ? <span key={cue.start}>{cue.text}</span> : null}
    </p>
  );
}
