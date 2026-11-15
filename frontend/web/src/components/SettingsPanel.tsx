import { engine } from "../engine/store";
import { useSettings, type MotionPref } from "../settings/context";

const SPEEDS = [0.5, 0.75, 1];
const MOTION: readonly { value: MotionPref; label: string }[] = [
  { value: "system", label: "Follow my system setting" },
  { value: "reduce", label: "Reduce motion" },
  { value: "full", label: "Full motion" },
];

export function SettingsPanel() {
  const { settings, update } = useSettings();
  const pct = Math.round(settings.volume * 100);
  return (
    <details className="settings">
      <summary className="ghost">Settings</summary>
      <div className="settings-body">
        <h2>Settings</h2>
        <label className="check">
          <input
            type="checkbox"
            checked={settings.sound}
            onChange={(e) => {
              update({ sound: e.target.checked });
              if (e.target.checked) engine.unlock();
            }}
          />
          Sound
        </label>
        <div className="field">
          <label htmlFor="volume">Volume</label>
          <input
            id="volume"
            type="range"
            min={0}
            max={100}
            value={pct}
            aria-valuetext={`${pct} percent`}
            disabled={!settings.sound}
            onChange={(e) => update({ volume: Number(e.target.value) / 100 })}
          />
        </div>
        <fieldset>
          <legend>Playback speed</legend>
          {SPEEDS.map((s) => (
            <label key={s} className="check">
              <input
                type="radio"
                name="rate"
                checked={settings.rate === s}
                onChange={() => update({ rate: s })}
              />
              {s}×
            </label>
          ))}
        </fieldset>
        <label className="check">
          <input
            type="checkbox"
            checked={settings.shortcuts}
            onChange={(e) => update({ shortcuts: e.target.checked })}
          />
          Single-key shortcuts in the player
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={settings.captions}
            onChange={(e) => update({ captions: e.target.checked })}
          />
          Show descriptions on the video
        </label>
        <fieldset>
          <legend>Motion</legend>
          {MOTION.map((m) => (
            <label key={m.value} className="check">
              <input
                type="radio"
                name="motion"
                checked={settings.motion === m.value}
                onChange={() => update({ motion: m.value })}
              />
              {m.label}
            </label>
          ))}
        </fieldset>
      </div>
    </details>
  );
}
