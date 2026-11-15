import { useEffect, useRef, useState, type CSSProperties } from "react";
import { withTransition } from "../a11y/transition";
import { CHAPTERS, FIRST_CHAPTER } from "../chapters";
import { EarthGlobe } from "../components/EarthGlobe";
import { Icon } from "../components/Icon";
import { SceneLink } from "../components/SceneLink";
import { engine } from "../engine/store";
import {
  AIR_SAMPLES,
  BODY,
  CONTINENTS,
  NIGHT_SAMPLES,
  type Sample,
} from "../samples";
import { useSettings } from "../settings/context";

type Phase = "title" | "guide";

const delay = (s: number): CSSProperties =>
  ({ "--d": `${s}s` }) as CSSProperties;

const W = 1100;
const H = 620;
const CX = 550;
const CY = 310;
const R = 220;

const SLOTS = [
  { side: "left", y: 130 },
  { side: "left", y: 310 },
  { side: "left", y: 490 },
  { side: "right", y: 130 },
  { side: "right", y: 310 },
  { side: "right", y: 490 },
] as const;

function leader(i: number, on: boolean) {
  const { side, y } = SLOTS[i];
  const sx = side === "left" ? 240 : 860;
  const dx = CX - sx;
  const dy = CY - y;
  const d = Math.hypot(dx, dy);
  return {
    x1: sx,
    y1: y,
    x2: on ? CX : CX - (R * dx) / d,
    y2: on ? CY : CY - (R * dy) / d,
  };
}

export function HowToListen() {
  const [phase, setPhase] = useState<Phase>("title");
  const [playing, setPlaying] = useState<string | null>(null);
  const [globeTurning, setGlobeTurning] = useState(true);
  const { settings, update, reducedMotion } = useSettings();
  const heading = useRef<HTMLHeadingElement>(null);
  const audio = useRef<HTMLAudioElement>(null);
  const wanted = useRef<string | null>(null);

  useEffect(() => {
    document.title = "How to listen · EarthPod";
    heading.current?.focus();
  }, [phase]);

  useEffect(() => {
    const t = window.setTimeout(() => setGlobeTurning(false), 4500);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    const a = audio.current;
    return () => a?.pause();
  }, []);

  const toggle = (s: Sample) => {
    const a = audio.current;
    if (!a) return;
    if (playing === s.id) {
      a.pause();
      return;
    }
    engine.stop();
    if (!settings.sound) update({ sound: true });
    wanted.current = s.id;
    a.src = s.file;
    a.volume = settings.volume;
    a.play().catch(() => setPlaying(null));
  };

  const sampleButton = (s: Sample) => {
    const on = playing === s.id;
    return (
      <li key={s.id}>
        <button
          type="button"
          className="pin-button"
          aria-pressed={on}
          onClick={() => toggle(s)}
        >
          <Icon name={on ? "pause" : "play"} size={16} />
          <span className="pin-text">
            <span className="pin-title">{s.title}</span>
            <span className="pin-instrument">{s.meaning}</span>
          </span>
        </button>
      </li>
    );
  };

  const first = CHAPTERS[0];
  const focused = CONTINENTS.find((s) => s.id === playing);

  return (
    <>
      {phase === "title" ? (
        <section className="title-card" aria-labelledby="title-heading">
          <div className="title-globe" aria-hidden="true">
            <EarthGlobe spinning={!reducedMotion && globeTurning} speed={8} />
          </div>
          <h1
            id="title-heading"
            ref={heading}
            tabIndex={-1}
            className="title-xl reveal"
            style={delay(0.3)}
          >
            <span className="title-num">
              <span className="sr-only">Chapter </span>00
              <span className="sr-only">: </span>
            </span>
            How to listen
          </h1>
          <p id="title-logline" className="logline reveal" style={delay(0.8)}>
            Every sound stands for something you can see.
          </p>
          <button
            type="button"
            className="primary reveal"
            style={delay(1.2)}
            aria-describedby="title-logline"
            onClick={() => withTransition(() => setPhase("guide"))}
          >
            Meet the instruments <Icon name="arrow" size={18} />
          </button>
        </section>
      ) : (
        <section className="guide" aria-labelledby="guide-heading">
          <h1
            id="guide-heading"
            ref={heading}
            tabIndex={-1}
            className="reveal"
            style={delay(0.1)}
          >
            Meet the instruments
          </h1>
          <p className="lede reveal" style={delay(0.2)}>
            Sonification is turning data into sound so you can hear patterns
            that are hard to see. Instead of looking at a graph, a video or an
            image, you listen to changes in pitch, volume or rhythm to
            understand the information.
          </p>
          <p className="lede reveal" style={delay(0.3)}>
            Each chapter has its own sounds. Play each one once: you will hear
            them again in the chapter.
          </p>

          <section
            className="guide-chapter reveal"
            style={delay(0.5)}
            aria-labelledby="g01"
          >
            <h2 id="g01" className="guide-sub">
              <span className="num">01</span> {CHAPTERS[0].title}
            </h2>
            <p id="continents-note" className="guide-note">
              Each continent has its own instrument and plays while it is on
              screen. Higher notes mean more dense CO₂ there.
            </p>
            <div className="pins">
              <div className="pins-globe" aria-hidden="true">
                <EarthGlobe
                  spinning={false}
                  focusLon={focused?.lon}
                  focusLat={focused?.lat}
                  instant={reducedMotion}
                />
              </div>
              <svg
                className="pins-lines"
                viewBox={`0 0 ${W} ${H}`}
                aria-hidden="true"
              >
                {CONTINENTS.map((s, i) => {
                  const l = leader(i, s.id === playing);
                  return (
                    <g
                      key={s.id}
                      className={s.id === playing ? "is-on" : undefined}
                    >
                      <line {...l} />
                      <rect x={l.x2 - 4} y={l.y2 - 4} width={8} height={8} />
                    </g>
                  );
                })}
              </svg>
              <ul className="pins-list">
                {CONTINENTS.map((s, i) => {
                  const on = playing === s.id;
                  return (
                    <li
                      key={s.id}
                      className={`pin pin-${SLOTS[i].side}`}
                      style={
                        { "--y": `${(SLOTS[i].y / H) * 100}%` } as CSSProperties
                      }
                    >
                      <button
                        type="button"
                        className="pin-button"
                        aria-pressed={on}
                        aria-describedby="continents-note"
                        onClick={() => toggle(s)}
                      >
                        <Icon name={on ? "pause" : "play"} size={16} />
                        <span className="pin-text">
                          <span className="pin-title">{s.title}</span>
                          <span className="pin-instrument">{s.instrument}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
            <h3 className="guide-small">Underneath the whole chapter</h3>
            <ul className="body-list">{BODY.map(sampleButton)}</ul>
          </section>

          <section
            className="guide-chapter reveal"
            style={delay(0.7)}
            aria-labelledby="g02"
          >
            <h2 id="g02" className="guide-sub">
              <span className="num">02</span> {CHAPTERS[1].title}
            </h2>
            <p className="guide-note">
              Left is west, right is east, and higher notes are further north.
            </p>
            <ul className="body-list">{NIGHT_SAMPLES.map(sampleButton)}</ul>
          </section>

          <section
            className="guide-chapter reveal"
            style={delay(0.9)}
            aria-labelledby="g03"
          >
            <h2 id="g03" className="guide-sub">
              <span className="num">03</span> {CHAPTERS[2].title}
            </h2>
            <p className="guide-note">
              A line scans the map from west to east. Each band of latitude has
              its own note, higher further north.
            </p>
            <ul className="body-list">{AIR_SAMPLES.map(sampleButton)}</ul>
          </section>

          <div className="end-actions reveal" style={delay(1.1)}>
            <SceneLink href={`/${FIRST_CHAPTER}`} className="primary">
              Next: {first.num} {first.short} <Icon name="arrow" size={18} />
            </SceneLink>
          </div>
        </section>
      )}
      {/* eslint-disable-next-line jsx-a11y/media-has-caption -- instrument samples with no speech; each button's name and description are the text alternative */}
      <audio
        ref={audio}
        preload="none"
        onPlaying={() => setPlaying(wanted.current)}
        onPause={(e) => {
          if (e.currentTarget.paused) setPlaying(null);
        }}
        onEnded={() => setPlaying(null)}
        onError={() => setPlaying(null)}
      />
    </>
  );
}
