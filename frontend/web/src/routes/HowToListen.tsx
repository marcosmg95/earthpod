import { useEffect, useRef, useState, type CSSProperties } from "react";
import { withTransition } from "../a11y/transition";
import { CHAPTERS, FIRST_CHAPTER } from "../chapters";
import { EarthGlobe } from "../components/EarthGlobe";
import { Icon } from "../components/Icon";
import { SceneLink } from "../components/SceneLink";
import { engine } from "../engine/store";
import { BODY, CONTINENTS, type Sample } from "../samples";
import { useSettings } from "../settings/context";

type Phase = "title" | "guide";

const delay = (s: number): CSSProperties =>
  ({ "--d": `${s}s` }) as CSSProperties;

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

  // the title-card globe turns for under 5 s, then rests (WCAG 2.2.2)
  useEffect(() => {
    const t = window.setTimeout(() => setGlobeTurning(false), 4500);
    return () => window.clearTimeout(t);
  }, []);

  // leaving the page: silence
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
    engine.stop(); // never two sounds at once
    if (!settings.sound) update({ sound: true });
    wanted.current = s.id;
    a.src = s.file;
    a.volume = settings.volume;
    a.play().catch(() => setPlaying(null));
  };

  const card = (s: Sample) => {
    const on = playing === s.id;
    return (
      <li key={s.id} className={`sample${on ? " is-playing" : ""}`}>
        <button
          type="button"
          className="sample-button"
          aria-pressed={on}
          aria-describedby={`${s.id}-meaning`}
          onClick={() => toggle(s)}
        >
          <span className="sample-icon" aria-hidden="true">
            <Icon name={on ? "pause" : "play"} size={20} />
          </span>
          <span className="sample-text">
            <span className="sample-title">{s.title}</span>
            {s.instrument !== s.title && (
              <span className="sample-instrument">{s.instrument}</span>
            )}
          </span>
          <span className="sample-bars" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
          </span>
        </button>
        <p id={`${s.id}-meaning`} className="sample-meaning">
          {s.meaning}
        </p>
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
          <p className="lede reveal" style={delay(0.3)}>
            Each part of the world has its own instrument. When it comes into
            view, you hear it.
          </p>

          <h2 className="guide-sub reveal" style={delay(0.5)}>
            The planet’s body
          </h2>
          <ul className="sample-grid reveal" style={delay(0.6)}>
            {BODY.map(card)}
          </ul>

          <h2 className="guide-sub reveal" style={delay(0.8)}>
            Six continents, six instruments
          </h2>
          <div className="guide-continents reveal" style={delay(0.9)}>
            <div className="guide-globe" aria-hidden="true">
              <EarthGlobe
                spinning={false}
                focusLon={focused?.lon}
                focusLat={focused?.lat}
                instant={reducedMotion}
              />
            </div>
            <ul className="sample-grid">{CONTINENTS.map(card)}</ul>
          </div>

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
