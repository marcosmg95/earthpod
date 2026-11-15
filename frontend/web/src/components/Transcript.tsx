import type { LoadedTrack } from "../data/useTrack";
import { engine } from "../engine/store";
import { mmss } from "../data/time";

export function Transcript({ track }: { track: LoadedTrack }) {
  if (!track.cues.length) return null;
  return (
    <table className="transcript">
      <caption className="sr-only">
        {track.title}: what happens. Choose a time to go there.
      </caption>
      <thead>
        <tr>
          <th scope="col">Time</th>
          <th scope="col">What happens</th>
        </tr>
      </thead>
      <tbody>
        {track.cues.map((c) => (
          <tr key={c.start}>
            <td>
              <button
                type="button"
                className="link"
                onClick={() => engine.seekTime(c.start)}
              >
                {mmss(c.start)}
              </button>
            </td>
            <td>{c.text}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
