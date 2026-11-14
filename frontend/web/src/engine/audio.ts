type WebkitWindow = Window & { webkitAudioContext?: typeof AudioContext };

let ctx: AudioContext | null = null;

export function audioContext(): AudioContext {
  if (!ctx) {
    const AC =
      window.AudioContext ?? (window as WebkitWindow).webkitAudioContext;
    if (!AC) throw new Error("Web Audio is not supported in this browser");
    ctx = new AC();
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

export const existingAudioContext = (): AudioContext | null => ctx;

export const midiHz = (m: number): number => 440 * 2 ** ((m - 69) / 12);
