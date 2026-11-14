// Turns an audio file into a small summary to draw: how loud and how bright the sound is over time.

export interface Peaks {
  /** loudness per bin, 0..1 */
  level: Float32Array;
  /** brightness per bin, 0..1: how often the wave crosses zero, a rough measure of how high it sounds */
  bright: Float32Array;
  duration: number;
}

const BINS = 480;
const cache = new Map<string, Promise<Peaks>>();

function normalise(a: Float32Array, p: number): void {
  const sorted = Float32Array.from(a).sort();
  const top = Math.max(
    1e-6,
    sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))],
  );
  for (let i = 0; i < a.length; i++) a[i] = Math.min(1, a[i] / top);
}

async function analyse(url: string): Promise<Peaks> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  // an offline context decodes without asking for sound permission
  const buf = await new OfflineAudioContext(1, 1, 44100).decodeAudioData(
    await res.arrayBuffer(),
  );
  const chans = Array.from(
    { length: Math.min(2, buf.numberOfChannels) },
    (_, c) => buf.getChannelData(c),
  );
  const n = buf.length;
  const per = Math.max(1, Math.floor(n / BINS));
  const level = new Float32Array(BINS);
  const bright = new Float32Array(BINS);
  for (let b = 0; b < BINS; b++) {
    const start = b * per;
    const end = Math.min(n, start + per);
    let sum = 0;
    let cross = 0;
    let prev = 0;
    for (let i = start; i < end; i++) {
      let s = 0;
      for (const ch of chans) s += ch[i];
      s /= chans.length;
      sum += s * s;
      if (s >= 0 !== prev >= 0) cross++;
      prev = s;
    }
    const len = Math.max(1, end - start);
    level[b] = Math.sqrt(sum / len);
    bright[b] = cross / len;
  }
  normalise(level, 1);
  normalise(bright, 0.95);
  return { level, bright, duration: buf.duration };
}

export function loadPeaks(url: string): Promise<Peaks> {
  let p = cache.get(url);
  if (!p) {
    p = analyse(url);
    cache.set(url, p);
    p.catch(() => cache.delete(url));
  }
  return p;
}

/** One sentence for screen readers: the text version of the chart. */
export function describePeaks(p: Peaks, label: (t: number) => string): string {
  const at = (i: number) => label(((i + 0.5) / p.level.length) * p.duration);
  let loud = 0;
  let high = -1;
  for (let i = 0; i < p.level.length; i++) {
    if (p.level[i] > p.level[loud]) loud = i;
    if (p.level[i] > 0.2 && (high < 0 || p.bright[i] > p.bright[high]))
      high = i;
  }
  const highPart = high >= 0 ? ` and at its highest around ${at(high)}` : "";
  return `Sound chart: the sound is loudest around ${at(loud)}${highPart}.`;
}
