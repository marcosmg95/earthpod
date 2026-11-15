import { useEffect, useRef } from "react";
import { CHAPTERS, type TrackRef } from "../chapters";
import { SceneLink } from "../components/SceneLink";
import { useTrack } from "../data/useTrack";

const pad = (n: number): string => String(n).padStart(2, "0");

function Poster({ track: ref }: { track: TrackRef }) {
  const { track } = useTrack(ref);
  const first = track?.frames[0];
  return (
    <div className="poster" aria-hidden="true">
      {track?.video ? (
        <video
          src={`${track.base}${track.video}#t=1`}
          muted
          playsInline
          preload="metadata"
        />
      ) : track && first ? (
        <img src={track.base + first.image} alt="" />
      ) : null}
    </div>
  );
}

export function RecordPage() {
  const h1 = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    document.title = "Record · EarthPod";
    h1.current?.focus();
  }, []);

  return (
    <section className="page" aria-labelledby="record-title">
      <div className="head-text">
        <h1 id="record-title" ref={h1} tabIndex={-1}>
          Record
        </h1>
        <p className="mapping">
          Every chapter, ready to replay. Open one from its title card, or go
          straight to a scene.
        </p>
      </div>
      <ul className="chapter-cards">
        {CHAPTERS.map((c) => (
          <li key={c.id}>
            <article className="chapter-card" aria-labelledby={`cc-${c.id}`}>
              <Poster track={c.tracks[0]} />
              <div className="chapter-card-body">
                <p className="kicker">Chapter {c.num}</p>
                <h2 id={`cc-${c.id}`}>
                  <SceneLink href={`/${c.id}`}>{c.title}</SceneLink>
                </h2>
                <p className="logline">{c.logline}</p>
                {c.tracks.length > 1 && (
                  <ol
                    className="scene-links"
                    aria-label={`Scenes of ${c.title}`}
                  >
                    {c.tracks.map((t, i) => (
                      <li key={t.id}>
                        <SceneLink href={`/${c.id}/${t.id}`}>
                          <span className="num">{pad(i + 1)}</span>
                          {t.label}
                        </SceneLink>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </article>
          </li>
        ))}
      </ul>
    </section>
  );
}
