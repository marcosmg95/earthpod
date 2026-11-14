// Explore: a short plain tone for one spot of the picture. Higher value = higher pitch (two octaves).
import { audioContext, midiHz } from "./audio";

export function probe(value: number, volume = 0.8): void {
  const ctx = audioContext();
  const t = ctx.currentTime + 0.01;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = "sine";
  o.frequency.value = midiHz(
    57 + Math.round(Math.max(0, Math.min(1, value)) * 24),
  );
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.25 * volume, t + 0.02);
  g.gain.setTargetAtTime(0, t + 0.25, 0.08);
  o.connect(g).connect(ctx.destination);
  o.start(t);
  o.stop(t + 0.8);
}
