import { useEffect, useRef, useState, type ReactNode } from "react";
import { mmss } from "../data/time";
import type { LoadedTrack } from "../data/useTrack";
import { useEngine } from "../engine/store";
import { useSettings } from "../settings/context";

function VideoPicture({ track }: { track: LoadedTrack }) {
  const { playing, time, duration } = useEngine();
  const { settings } = useSettings();
  const ref = useRef<HTMLVideoElement>(null);
  const [videoLen, setVideoLen] = useState(0);
  const [failed, setFailed] = useState(false);

  const stretch = duration > 0 && videoLen > 0 ? videoLen / duration : 1;

  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    v.playbackRate = settings.rate * stretch;
    if (playing) v.play().catch(() => undefined);
    else v.pause();
  }, [playing, settings.rate, stretch]);

  useEffect(() => {
    const v = ref.current;
    if (!v || !videoLen || v.seeking) return;
    const target = time * stretch;
    const limit = playing ? 0.75 : 0.05;
    if (Math.abs(v.currentTime - target) > limit) v.currentTime = target;
  }, [time, stretch, videoLen, playing]);

  return (
    <>
      <video
        ref={ref}
        src={track.base + (track.video ?? "")}
        muted
        playsInline
        preload="auto"
        aria-hidden="true"
        onLoadedMetadata={(e) => setVideoLen(e.currentTarget.duration)}
        onError={() => setFailed(true)}
      />
      {failed && (
        <p className="frame-error">
          This browser cannot play the video file. The sound still works. Ask
          for an H.264 (MP4) export.
        </p>
      )}
      <p className="sr-only">
        Moving picture: {track.title}. Press D to hear what is on screen now, or
        turn on Descriptions to hear them as the scene plays.
      </p>
      <div className="hud" aria-hidden="true">
        <span>
          <small>Elapsed</small>
          {mmss(time)} / {mmss(duration)}
        </span>
      </div>
    </>
  );
}

function StillPicture({ track, frame }: { track: LoadedTrack; frame: number }) {
  const i = Math.min(frame, track.frames.length - 1);
  const f = track.frames[i];

  useEffect(() => {
    for (let k = 1; k <= 3; k++) {
      const n = track.frames[i + k];
      if (n) new Image().src = track.base + n.image;
    }
  }, [track, i]);

  return (
    <>
      <img
        src={track.base + f.image}
        alt={f.description ?? `${track.title}, ${f.label}`}
      />
      <div className="hud" aria-hidden="true">
        <span>
          <small>Time</small>
          {f.label}
        </span>
        <span>
          <small>Frame</small>
          {i + 1} / {track.frames.length}
        </span>
      </div>
    </>
  );
}

export function FrameView({
  track,
  frame,
  children,
}: {
  track: LoadedTrack;
  frame: number;
  children?: ReactNode;
}) {
  return (
    <figure className="frame">
      {track.video ? (
        <VideoPicture track={track} />
      ) : (
        <StillPicture track={track} frame={frame} />
      )}
      {children}
    </figure>
  );
}
