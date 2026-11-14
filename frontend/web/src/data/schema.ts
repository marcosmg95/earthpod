import { z } from "zod";

const num = z.number();

export const Frame = z.object({
  /** seconds into the audio when this frame appears */
  t: num.nonnegative(),
  /** path relative to the track folder */
  image: z.string(),
  /** short time label, e.g. "12 Feb 2020 06:00 UTC" or "2016" */
  label: z.string(),
  /** one sentence: alt text and the Describe button */
  description: z.string().optional(),
});

export const Region = z.object({
  name: z.string(),
  col: z.number().int().nonnegative(),
  row: z.number().int().nonnegative(),
});

export const Grid = z.object({
  cols: z.number().int().positive(),
  rows: z.number().int().positive(),
  /** what a high value means, e.g. "CO₂" or "light" */
  high: z.string(),
  /** frame index -> cols × rows values 0..1, row by row from the top. Key frames only. */
  values: z.record(z.string(), z.array(num.min(0).max(1))),
});

export const TrackManifest = z.object({
  id: z.string(),
  title: z.string(),
  /** e.g. "NASA SVS 5196" */
  source: z.string(),
  /** one sentence: how the sound follows the picture */
  mapping: z.string(),
  /** the first file the browser can play wins, e.g. ["audio.m4a", "audio.ogg"] */
  audio: z.array(z.string()).min(1),
  /** WebVTT file with time-coded descriptions of key moments */
  descriptions: z.string().optional(),
  frames: z.array(Frame).default([]),
  /** optional moving picture, played muted and kept in step with the audio */
  video: z.string().optional(),
  /** dates of the first and last moment, to label the timeline */
  dates: z.object({ start: z.string(), end: z.string() }).optional(),
  regions: z.array(Region).optional(),
  grid: Grid.optional(),
});

export type Frame = z.infer<typeof Frame>;
export type Region = z.infer<typeof Region>;
export type TrackManifest = z.infer<typeof TrackManifest>;

export async function loadTrack(url: string): Promise<TrackManifest> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} was not found (${res.status}).`);
  return TrackManifest.parse(await res.json());
}
