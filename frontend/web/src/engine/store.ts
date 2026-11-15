import { useSyncExternalStore } from "react";
import { say, setDucker } from "../a11y/announce";
import type { Frame } from "../data/schema";
import { timeLabel } from "../data/time";
import type { LoadedTrack } from "../data/useTrack";
import type { Cue } from "../data/vtt";
import { MediaPlayer } from "./media";

export interface EngineState {
  trackKey: string | null;
  playing: boolean;
  time: number;
  duration: number;
  frame: number;
  ended: boolean;
  error: string | null;
}

const STEP_SECONDS = 5;

let state: EngineState = {
  trackKey: null,
  playing: false,
  time: 0,
  duration: 0,
  frame: 0,
  ended: false,
  error: null,
};
let track: LoadedTrack | null = null;
let lastCue = -1;
let describeAlong = false;
const subs = new Set<() => void>();

function set(patch: Partial<EngineState>): void {
  state = { ...state, ...patch };
  subs.forEach((fn) => fn());
}

export function frameAt(
  frames: readonly { t: number }[],
  time: number,
): number {
  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (frames[mid].t <= time) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

export function cueAt(cues: readonly Cue[], time: number): number {
  return cues.findIndex((c) => time >= c.start && time < c.end);
}

function describeTime(time: number, withText = describeAlong): string {
  if (!track) return "";
  const f = track.frames[frameAt(track.frames, time)] as Frame | undefined;
  const cue = track.cues[cueAt(track.cues, time)] as Cue | undefined;
  const label = f?.label ?? timeLabel(track, time, state.duration);
  return [label, withText ? (f?.description ?? cue?.text) : undefined]
    .filter(Boolean)
    .join(". ");
}

const media = new MediaPlayer({
  onReady: (duration) => set({ duration }),
  onTime: (time) => {
    if (!track) return;
    const frame = frameAt(track.frames, time);
    if (frame !== state.frame || Math.abs(time - state.time) > 0.25)
      set({ time, frame });
    const c = cueAt(track.cues, time);
    if (c !== lastCue) {
      lastCue = c;
      if (c >= 0 && state.playing && describeAlong) say(track.cues[c].text);
    }
  },
  onPause: () => {
    if (state.playing) set({ playing: false });
  },
  onEnd: () => {
    set({ playing: false, ended: true });
    say("End of the track. Press Play to hear it again.", { force: true });
  },
  onError: (message) => set({ playing: false, error: message }),
});
setDucker((seconds) => media.duck(seconds));

function subscribe(fn: () => void): () => void {
  subs.add(fn);
  return () => {
    subs.delete(fn);
  };
}

const get = (): EngineState => state;

function load(key: string, t: LoadedTrack): void {
  if (state.trackKey === key) return;
  track = t;
  lastCue = -1;
  media.load(t.audio.map((a) => t.base + a));
  set({
    trackKey: key,
    playing: false,
    time: 0,
    duration: 0,
    frame: 0,
    ended: false,
    error: null,
  });
  if ("mediaSession" in navigator) {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: t.title,
      artist: "EarthPod",
      album: t.source,
    });
  }
}

function play(): void {
  if (!track) return;
  if (state.ended) media.seek(0);
  media
    .play()
    .then(() => set({ playing: true, ended: false, error: null }))
    .catch(() =>
      set({
        playing: false,
        error: "The browser did not start the sound. Press Play again.",
      }),
    );
}

function pause(announce = true): void {
  if (!state.playing) return;
  media.pause();
  set({ playing: false });
  if (announce) say(`Paused. ${describeTime(state.time)}`, { force: true });
}

function toggle(): void {
  if (state.playing) pause();
  else play();
}

function stop(): void {
  media.pause();
  set({ playing: false });
}

function now(): number {
  return media.el.currentTime;
}

function seekTime(time: number, announce = true): void {
  if (!track) return;
  const t = Math.max(0, state.duration ? Math.min(state.duration, time) : time);
  media.seek(t);
  const frame = frameAt(track.frames, t);
  lastCue = cueAt(track.cues, t);
  set({ time: t, frame, ended: false });
  if (announce) say(describeTime(t), { force: true });
}

function seekFrame(i: number, announce = true): void {
  if (!track || !track.frames.length) return;
  const f = Math.max(0, Math.min(track.frames.length - 1, i));
  seekTime(track.frames[f].t, announce);
}

function step(n: number): void {
  if (!track) return;
  if (track.frames.length) seekFrame(state.frame + n);
  else seekTime(state.time + n * STEP_SECONDS);
}

function describe(): void {
  say(describeTime(state.time, true), { force: true });
}

function unlock(): void {
  media.ensure();
}

function setVolume(v: number): void {
  media.setVolume(v);
}

function setRate(r: number): void {
  media.setRate(r);
}

function setDescriptions(on: boolean): void {
  describeAlong = on;
}

if ("mediaSession" in navigator) {
  navigator.mediaSession.setActionHandler("play", () => play());
  navigator.mediaSession.setActionHandler("pause", () => pause(false));
  navigator.mediaSession.setActionHandler("seekbackward", () => step(-2));
  navigator.mediaSession.setActionHandler("seekforward", () => step(2));
}

export const engine = {
  subscribe,
  get,
  load,
  play,
  pause,
  toggle,
  stop,
  now,
  seekTime,
  seekFrame,
  step,
  describe,
  unlock,
  setVolume,
  setRate,
  setDescriptions,
} as const;

export const useEngine = (): EngineState =>
  useSyncExternalStore(engine.subscribe, engine.get);
