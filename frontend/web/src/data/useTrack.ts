import { useEffect, useState } from "react";
import type { TrackRef } from "../chapters";
import { loadTrack, type TrackManifest } from "./schema";
import { parseVtt, type Cue } from "./vtt";

export interface LoadedTrack extends TrackManifest {
  base: string;
  cues: Cue[];
}

const cache = new Map<string, Promise<LoadedTrack>>();

async function fetchVtt(url: string): Promise<Cue[]> {
  const res = await fetch(url);
  const text = res.ok ? await res.text() : "";
  return text.startsWith("WEBVTT") ? parseVtt(text) : [];
}

async function fetchMedia(ref: TrackRef): Promise<LoadedTrack> {
  const base = "data/";
  const head = await fetch(`${base}${ref.dir}.wav`, { method: "HEAD" });
  if (
    !head.ok ||
    !(head.headers.get("content-type") ?? "").startsWith("audio")
  ) {
    throw new Error(`public/data/${ref.dir}.wav was not found.`);
  }
  return {
    id: ref.dir,
    title: ref.label,
    source: ref.source,
    mapping: ref.mapping ?? "",
    audio: [`${ref.dir}.wav`],
    video: `${ref.dir}.mp4`,
    frames: [],
    dates:
      ref.start && ref.end ? { start: ref.start, end: ref.end } : undefined,
    base,
    cues: await fetchVtt(`${base}${ref.dir}.vtt`),
  };
}

async function fetchManifest(dir: string): Promise<LoadedTrack> {
  const base = `data/${dir}/`;
  const manifest = await loadTrack(`${base}track.json`);
  const cues = manifest.descriptions
    ? await fetchVtt(base + manifest.descriptions)
    : [];
  return { ...manifest, base, cues };
}

interface TrackState {
  dir: string | null;
  track: LoadedTrack | null;
  error: string | null;
}

export function useTrack(ref: TrackRef | null): TrackState {
  const dir = ref?.dir ?? null;
  const [s, setS] = useState<TrackState>({
    dir: null,
    track: null,
    error: null,
  });
  useEffect(() => {
    if (!ref) return;
    let alive = true;
    let p = cache.get(ref.dir);
    if (!p) {
      p = ref.manifest ? fetchManifest(ref.dir) : fetchMedia(ref);
      cache.set(ref.dir, p);
    }
    p.then((track) => {
      if (alive) setS({ dir: ref.dir, track, error: null });
    }).catch((e: unknown) => {
      cache.delete(ref.dir);
      if (alive)
        setS({
          dir: ref.dir,
          track: null,
          error: e instanceof Error ? e.message : String(e),
        });
    });
    return () => {
      alive = false;
    };
  }, [ref]);
  return s.dir === dir ? s : { dir, track: null, error: null };
}
