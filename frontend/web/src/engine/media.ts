import { audioContext } from "./audio";

export interface MediaCallbacks {
  onReady?: (duration: number) => void;
  onTime?: (time: number) => void;
  onPause?: () => void;
  onEnd?: () => void;
  onError?: (message: string) => void;
}

const MIME: Record<string, string> = {
  m4a: "audio/mp4",
  mp4: "audio/mp4",
  aac: "audio/aac",
  mp3: "audio/mpeg",
  ogg: "audio/ogg",
  opus: "audio/ogg",
  wav: "audio/wav",
  webm: "audio/webm",
  flac: "audio/flac",
};
const mimeOf = (src: string): string =>
  MIME[src.split("?")[0].split(".").pop()?.toLowerCase() ?? ""] ?? "";

export class MediaPlayer {
  readonly el: HTMLAudioElement;
  private duckGain: GainNode | null = null;
  private raf = 0;
  private readonly cb: MediaCallbacks;

  constructor(callbacks: MediaCallbacks = {}) {
    this.cb = callbacks;
    const el = new Audio();
    el.preload = "auto";
    el.preservesPitch = true;
    el.addEventListener("loadedmetadata", () => this.cb.onReady?.(el.duration));
    el.addEventListener("seeked", () => this.cb.onTime?.(el.currentTime));
    el.addEventListener("pause", () => {
      this.stopLoop();
      this.cb.onPause?.();
    });
    el.addEventListener("ended", () => this.cb.onEnd?.());
    el.addEventListener("error", () =>
      this.cb.onError?.("The audio file could not be played."),
    );
    this.el = el;
  }

  load(sources: string[]): void {
    this.el.pause();
    const playable = sources.find((s) => this.el.canPlayType(mimeOf(s)) !== "");
    this.el.src = playable ?? sources[0];
    this.el.load();
  }

  ensure(): void {
    if (this.duckGain) return;
    const ctx = audioContext();
    const g = ctx.createGain();
    ctx.createMediaElementSource(this.el).connect(g).connect(ctx.destination);
    this.duckGain = g;
  }

  async play(): Promise<void> {
    this.ensure();
    await this.el.play();
    this.loop();
  }

  pause(): void {
    this.el.pause();
  }

  seek(time: number): void {
    const d = Number.isFinite(this.el.duration) ? this.el.duration : Infinity;
    this.el.currentTime = Math.max(0, Math.min(d, time));
  }

  setRate(rate: number): void {
    this.el.playbackRate = rate;
  }

  setVolume(v: number): void {
    this.el.volume = Math.max(0, Math.min(1, v));
  }

  duck(seconds: number): void {
    const g = this.duckGain;
    if (!g || this.el.paused) return;
    const t = g.context.currentTime;
    g.gain.cancelScheduledValues(t);
    g.gain.setTargetAtTime(0.35, t, 0.05);
    g.gain.setTargetAtTime(1, t + seconds, 0.3);
  }

  private loop(): void {
    this.stopLoop();
    const tick = (): void => {
      this.cb.onTime?.(this.el.currentTime);
      if (!this.el.paused) this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  private stopLoop(): void {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
  }
}
