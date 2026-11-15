import type { LoadedTrack } from "./useTrack";

export const mmss = (t: number): string =>
  `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

const dateFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function timeLabel(
  track: LoadedTrack,
  t: number,
  duration: number,
): string {
  if (track.scan && duration > 0) {
    const f = Math.min(1, Math.max(0, t / duration));
    const lon = Math.round(
      track.scan.from + (track.scan.to - track.scan.from) * f,
    );
    return lon === 0 ? "0°" : `${Math.abs(lon)}°${lon < 0 ? "W" : "E"}`;
  }
  if (!track.dates || duration <= 0) return mmss(t);
  const a = Date.parse(track.dates.start);
  const b = Date.parse(track.dates.end);
  return dateFmt.format(
    new Date(a + (b - a) * Math.min(1, Math.max(0, t / duration))),
  );
}
