import { useEffect, useRef, useState, type ReactNode } from "react";
import { timeLabel } from "../data/time";
import type { LoadedTrack } from "../data/useTrack";
import { engine, useEngine } from "../engine/store";
import { describePeaks, loadPeaks, type Peaks } from "../engine/waveform";

type RGB = [number, number, number];
const rgb = (hex: string): RGB => {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as RGB;
};
const mix = (a: RGB, b: RGB, t: number): string =>
  `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * t)).join(",")})`;

interface Props {
  track: LoadedTrack;
  /** id of the sentence that describes the chart; the slider points to it */
  descriptionId: string;
  /** the real slider, laid over the chart */
  children: ReactNode;
}

/** A picture of the sound: height = loudness, colour = how high it sounds, marks = key moments. */
export function SoundChart({ track, descriptionId, children }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { duration } = useEngine();
  const src = track.base + track.audio[0];
  const [state, setState] = useState<{ src: string; peaks: Peaks | null }>({
    src: "",
    peaks: null,
  });
  const peaks = state.src === src ? state.peaks : null;

  useEffect(() => {
    let alive = true;
    loadPeaks(src)
      .then((p) => {
        if (alive) setState({ src, peaks: p });
      })
      .catch(() => undefined); // no chart: the slider still works
    return () => {
      alive = false;
    };
  }, [src]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const css = getComputedStyle(canvas);
    const v = (name: string, fallback: string) =>
      css.getPropertyValue(name).trim() || fallback;
    const teal = rgb(v("--teal", "#4fb3b3"));
    const yellow = rgb(v("--yellow", "#eeaa11"));
    const ink = v("--ink", "#e7e4de");
    const berry = v("--berry", "#bb3381");
    const colors = peaks
      ? Array.from(peaks.bright, (b) => mix(teal, yellow, b))
      : [];

    let w = 0;
    let h = 0;
    let raf = 0;
    let lastT = -1;
    let dirty = true;

    const resize = () => {
      const r = canvas.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      w = r.width;
      h = r.height;
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dirty = true;
    };
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();

    const render = (t: number, total: number) => {
      ctx.clearRect(0, 0, w, h);
      const mid = h / 2;
      const px = total > 0 ? Math.min(1, t / total) * w : 0;
      if (peaks) {
        const n = peaks.level.length;
        const step = w / n;
        const barW = Math.max(1, step * 0.6);
        for (let i = 0; i < n; i++) {
          const x = i * step;
          const amp = Math.max(1, peaks.level[i] * (mid - 2));
          ctx.globalAlpha = x + barW <= px ? 1 : 0.3; // played part bright, the rest dim
          ctx.fillStyle = colors[i];
          ctx.fillRect(x, mid - amp, barW, amp * 2);
        }
      } else {
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = ink;
        ctx.fillRect(0, mid - 1, w, 2);
      }
      ctx.globalAlpha = 1;
      ctx.fillStyle = berry; // key moments from the descriptions
      if (total > 0)
        for (const c of track.cues)
          ctx.fillRect((c.start / total) * w - 1, 0, 2, 8);
      ctx.fillStyle = ink; // playhead
      ctx.fillRect(px - 1, 0, 2, h);
    };

    const loop = () => {
      const total = engine.get().duration || peaks?.duration || 0;
      const t = engine.now();
      if (dirty || t !== lastT) {
        render(t, total);
        lastT = t;
        dirty = false;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [peaks, track]);

  const label = (t: number) =>
    timeLabel(track, t, duration || peaks?.duration || 0);

  return (
    <div className="sound-chart">
      <canvas ref={canvasRef} aria-hidden="true" />
      {children}
      <p id={descriptionId} className="sr-only">
        {peaks ? describePeaks(peaks, label) : "The sound chart is loading."}
      </p>
    </div>
  );
}
