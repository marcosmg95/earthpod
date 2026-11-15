import { useState, type ReactNode } from "react";
import { mmss, timeLabel } from "../data/time";
import type { LoadedTrack } from "../data/useTrack";
import { engine, useEngine } from "../engine/store";
import { useSettings } from "../settings/context";
import { Icon } from "./Icon";
import { SoundChart } from "./SoundChart";

const SPEEDS = [0.5, 0.75, 1];

export function Player({
  track,
  children,
}: {
  track: LoadedTrack;
  children?: ReactNode;
}) {
  const { playing, frame, time, duration } = useEngine();
  const { settings, update } = useSettings();
  const [open, setOpen] = useState(false);

  const timeBased = track.frames.length === 0;
  const last = timeBased
    ? Math.max(1, Math.floor(duration))
    : track.frames.length - 1;
  const value = timeBased
    ? Math.min(last, Math.floor(time))
    : Math.min(frame, last);
  const label = timeBased
    ? timeLabel(track, time, duration)
    : track.frames[value].label;
  const valuetext = timeBased
    ? `${label}. ${mmss(time)} of ${mmss(duration)}`
    : `${label}. Frame ${value + 1} of ${last + 1}`;
  const first = timeBased
    ? timeLabel(track, 0, duration)
    : track.frames[0].label;
  const end = timeBased
    ? timeLabel(track, duration, duration)
    : track.frames[last].label;
  const hasMoments = track.cues.length > 0;

  return (
    <section className="player" aria-label="Player">
      <button
        type="button"
        className="play"
        aria-label={playing ? "Pause" : "Play"}
        aria-keyshortcuts={settings.shortcuts ? "Space" : undefined}
        onClick={engine.toggle}
      >
        <Icon name={playing ? "pause" : "play"} size={24} />
      </button>

      <div className="timeline">
        <SoundChart track={track} descriptionId="sound-summary">
          <label htmlFor="position" className="sr-only">
            Position
          </label>
          <input
            id="position"
            type="range"
            min={0}
            max={last}
            step={1}
            value={value}
            aria-valuetext={valuetext}
            aria-describedby="sound-summary"
            onChange={(e) => {
              const v = Number(e.target.value);
              if (timeBased) engine.seekTime(v, false);
              else engine.seekFrame(v, false);
            }}
          />
        </SoundChart>
        <div className="ends" aria-hidden="true">
          <span>{first}</span>
          <span>{end}</span>
        </div>
      </div>

      <button
        type="button"
        className="options-toggle"
        aria-expanded={open}
        aria-controls="player-options"
        data-tip="Options"
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name="sliders" size={22} />
        <span className="sr-only">Options</span>
      </button>

      <div id="player-options" className="options-panel" hidden={!open}>
        <div className="options-row">
          <fieldset className="speed">
            <legend className="options-label">Speed</legend>
            <span className="speed-group">
              {SPEEDS.map((s) => (
                <label key={s} className="seg">
                  <input
                    type="radio"
                    name="speed"
                    checked={settings.rate === s}
                    onChange={() => update({ rate: s })}
                  />
                  {s}×
                </label>
              ))}
            </span>
          </fieldset>
          {hasMoments && (
            <button
              type="button"
              className="ghost"
              onClick={engine.describe}
              aria-keyshortcuts={settings.shortcuts ? "D" : undefined}
            >
              <Icon name="text" /> Describe this moment
            </button>
          )}
        </div>

        <div className="chart-key">
          <span className="options-label">Key</span>
          <span className="key-item">
            <i className="key-tone" aria-hidden="true" /> low → high tone
          </span>
          <span className="key-item">
            <i className="key-height" aria-hidden="true" /> height = loudness
          </span>
          {hasMoments && (
            <span className="key-item">
              <i className="key-moment" aria-hidden="true" /> key moment
            </span>
          )}
        </div>

        {hasMoments && children && (
          <div className="options-transcript">{children}</div>
        )}
      </div>
    </section>
  );
}
