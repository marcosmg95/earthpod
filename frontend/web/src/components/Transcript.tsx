import type { LoadedTrack } from "../data/useTrack";
import { engine } from "../engine/store";

const mmss = (t: number): string =>
  `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

export function Transcript({ track }: { track: LoadedTrack }) {
  const rows = track.cues.length
    ? track.cues.map((c) => ({ t: c.start, text: c.text }))
    : track.frames
        .filter((f) => f.description)
        .map((f) => ({ t: f.t, text: `${f.label}: ${f.description}` }));

  return (
    <details className="transcript">
      <summary>
        <span>Transcript: key moments as text</span>
        <span className="count">{rows.length}</span>
      </summary>
      {rows.length ? (
        <table>
          <caption className="sr-only">
            {track.title}: key moments. Choose a time to go there.
          </caption>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">What happens</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, k) => (
              <tr key={k}>
                <td>
                  <button
                    type="button"
                    className="link"
                    onClick={() => engine.seekTime(r.t)}
                  >
                    {mmss(r.t)}
                  </button>
                </td>
                <td>{r.text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No descriptions yet.</p>
      )}
    </details>
  );
}
