import { useEffect, useRef, useState } from "react";
import { say } from "../a11y/announce";
import { CHAPTERS } from "../chapters";
import { FrameView } from "../components/FrameView";
import { Icon } from "../components/Icon";
import { useTrack, type LoadedTrack } from "../data/useTrack";
import { probe } from "../engine/probe";
import { engine, useEngine } from "../engine/store";
import { useSettings } from "../settings/context";

const PICTURES = CHAPTERS.flatMap((c) =>
  c.tracks.map((t) => ({ ...t, chapter: c.short })),
);

interface Cell {
  col: number;
  row: number;
}

const level = (v: number): number => Math.min(5, 1 + Math.floor(v * 5));

function nearestKey(track: LoadedTrack, frame: number): number | null {
  const keys = Object.keys(track.grid?.values ?? {}).map(Number);
  if (!keys.length) return null;
  return keys.reduce((best, k) =>
    Math.abs(k - frame) < Math.abs(best - frame) ? k : best,
  );
}

export function ExplorePage() {
  const [dir, setDir] = useState(PICTURES[0].dir);
  const picture = PICTURES.find((p) => p.dir === dir) ?? PICTURES[0];
  const { track, error } = useTrack(picture);
  const { trackKey, frame } = useEngine();
  const { settings } = useSettings();
  const [cur, setCur] = useState<Cell>({ col: 0, row: 0 });
  const area = useRef<HTMLDivElement>(null);
  const h1 = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = "Explore · EarthPod";
    h1.current?.focus();
    engine.stop();
  }, []);

  useEffect(() => {
    if (track) engine.load(dir, track);
  }, [dir, track]);

  const grid = track?.grid;
  const key = track ? nearestKey(track, trackKey === dir ? frame : 0) : null;
  const values = grid && key !== null ? grid.values[String(key)] : undefined;

  const nameAt = (c: Cell): string =>
    track?.regions?.find(
      (r) => Math.abs(r.col - c.col) <= 1 && Math.abs(r.row - c.row) <= 1,
    )?.name ?? `Column ${c.col + 1}, row ${c.row + 1}`;
  const valueAt = (c: Cell): number =>
    grid && values ? (values[c.row * grid.cols + c.col] ?? 0) : 0;

  const sound = (c: Cell): void => {
    const v = valueAt(c);
    if (settings.sound) probe(v, settings.volume);
    say(`${nameAt(c)}: level ${level(v)} of 5`, { force: true });
  };

  const moveTo = (c: Cell): void => {
    if (!grid) return;
    const next = {
      col: Math.max(0, Math.min(grid.cols - 1, c.col)),
      row: Math.max(0, Math.min(grid.rows - 1, c.row)),
    };
    setCur(next);
    sound(next);
  };

  // the key and pointer listeners always call the latest moveTo / sound
  const latest = useRef({ moveTo, sound, cur });
  useEffect(() => {
    latest.current = { moveTo, sound, cur };
  });

  useEffect(() => {
    const el = area.current;
    if (!el || !grid) return;
    const onKey = (e: KeyboardEvent): void => {
      const { moveTo: go, sound: play, cur: c } = latest.current;
      const n = e.shiftKey ? 5 : 1;
      const moves: Record<string, [number, number]> = {
        ArrowLeft: [-n, 0],
        ArrowRight: [n, 0],
        ArrowUp: [0, -n],
        ArrowDown: [0, n],
      };
      const m = moves[e.key] as [number, number] | undefined;
      if (m) {
        e.preventDefault();
        go({ col: c.col + m[0], row: c.row + m[1] });
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        play(c);
      }
    };
    const onPointer = (e: PointerEvent): void => {
      const r = el.getBoundingClientRect();
      latest.current.moveTo({
        col: Math.floor(((e.clientX - r.left) / r.width) * grid.cols),
        row: Math.floor(((e.clientY - r.top) / r.height) * grid.rows),
      });
    };
    el.addEventListener("keydown", onKey);
    el.addEventListener("pointerdown", onPointer);
    return () => {
      el.removeEventListener("keydown", onKey);
      el.removeEventListener("pointerdown", onPointer);
    };
  }, [grid]);

  return (
    <section className="page" aria-labelledby="explore-title">
      <div className="chapter-head">
        <div className="head-text">
          <p className="kicker">Explore a picture</p>
          <h1 id="explore-title" ref={h1} tabIndex={-1}>
            Explore
          </h1>
          <p className="mapping">
            Move over the picture with the arrow keys, or tap it. Each spot
            plays a tone: the higher the tone, the more{" "}
            {grid?.high ?? "of what the picture shows"}.
          </p>
        </div>
        <div className="field">
          <label htmlFor="picture">Picture</label>
          <select
            id="picture"
            value={dir}
            onChange={(e) => setDir(e.target.value)}
          >
            {PICTURES.map((p) => (
              <option key={p.dir} value={p.dir}>
                {p.chapter}: {p.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <p role="alert" className="notice">
          This picture is not ready yet. {error}
        </p>
      )}
      {!error && !track && (
        <p role="status" className="notice">
          Loading…
        </p>
      )}
      {track && !grid && (
        <p className="notice">This picture has no values to explore yet.</p>
      )}

      {track && grid && (
        <div className="explore-layout">
          <div
            ref={area}
            className="explorer"
            role="application"
            aria-roledescription="picture explorer"
            aria-label={`${track.title}. Arrow keys move one spot, Shift and arrows move five, Enter plays the spot again.`}
            // tabIndex={0}
          >
            <FrameView track={track} frame={key ?? 0}>
              <div
                className="grid-overlay"
                aria-hidden="true"
                style={{
                  backgroundSize: `${100 / grid.cols}% ${100 / grid.rows}%`,
                }}
              />
              <div
                className="cursor"
                aria-hidden="true"
                style={{
                  left: `${(cur.col / grid.cols) * 100}%`,
                  top: `${(cur.row / grid.rows) * 100}%`,
                  width: `${100 / grid.cols}%`,
                  height: `${100 / grid.rows}%`,
                }}
              />
            </FrameView>
          </div>

          <aside className="cursor-panel" aria-label="Cursor">
            <p className="label">Cursor</p>
            <p className="cursor-name">{nameAt(cur)}</p>
            <p className="cursor-value">Level {level(valueAt(cur))} of 5</p>
            <button
              type="button"
              className="primary"
              onClick={() => sound(cur)}
            >
              <Icon name="wave" size={20} /> Play this spot
            </button>
            {track.regions?.length ? (
              <div className="jump">
                <h2 className="label">Jump to</h2>
                <ul>
                  {track.regions.map((r) => (
                    <li key={r.name}>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => moveTo({ col: r.col, row: r.row })}
                      >
                        <Icon name="target" size={16} /> {r.name}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <p className="hint">
              Arrows move one spot · Shift + arrows move five · Enter plays
              again
            </p>
          </aside>
        </div>
      )}
    </section>
  );
}
