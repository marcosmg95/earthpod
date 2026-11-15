import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "wouter";
import { withTransition } from "../a11y/transition";
import { EarthGlobe } from "../components/EarthGlobe";
import { Icon } from "../components/Icon";
import { parseVtt, type Cue } from "../data/vtt";
import { engine } from "../engine/store";
import { useSettings } from "../settings/context";

const NARRATION = [
  "I was born 4.54 billion years ago.",
  "300,000 years ago, I provided shelter to humans.",
  "Since then, we have shared countless experiences and witnessed many changes.",
  "This is our current era.",
];

type Phase = "ready" | "film";

const ease = (x: number): number =>
  x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;

export function Intro() {
  const [, navigate] = useLocation();
  const { settings, update, reducedMotion } = useSettings();
  const [phase, setPhase] = useState<Phase>("ready");
  const [line, setLine] = useState("");
  const [paused, setPaused] = useState(false);
  const [active, setActive] = useState(false);
  const [failed, setFailed] = useState(false);
  const [cues, setCues] = useState<Cue[]>([]);
  const audio = useRef<HTMLAudioElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const h1 = useRef<HTMLHeadingElement>(null);
  const filmHeading = useRef<HTMLHeadingElement>(null);
  const done = useRef(false);
  const endTimer = useRef(0);

  useEffect(() => {
    document.title = "EarthPod";
    h1.current?.focus();
    return () => window.clearTimeout(endTimer.current);
  }, []);

  const finish = useCallback(() => {
    if (done.current) return;
    done.current = true;
    audio.current?.pause();
    withTransition(() => navigate("/listen"));
  }, [navigate]);

  const toggle = useCallback(() => {
    const a = audio.current;
    if (!a) return;
    if (a.paused) a.play().catch(() => undefined);
    else a.pause();
  }, []);

  useEffect(() => {
    let alive = true;
    fetch("intro/narration.vtt")
      .then((r) => (r.ok ? r.text() : ""))
      .then((text) => {
        if (alive && text.startsWith("WEBVTT")) setCues(parseVtt(text));
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (phase !== "film") return;
    filmHeading.current?.focus();
    let raf = 0;
    const tick = () => {
      const a = audio.current;
      if (a && a.duration > 0) {
        stage.current?.style.setProperty(
          "--e",
          ease(Math.min(1, a.currentTime / (a.duration * 0.9))).toFixed(4),
        );
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  useEffect(() => {
    if (phase !== "film") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        finish();
      } else if (e.key === " " && !(e.target instanceof HTMLButtonElement)) {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, finish, toggle]);

  useEffect(() => {
    if (phase !== "film") return;
    let t = 0;
    const wake = () => {
      setActive(true);
      window.clearTimeout(t);
      t = window.setTimeout(() => setActive(false), 2500);
    };
    window.addEventListener("pointermove", wake);
    window.addEventListener("pointerdown", wake);
    return () => {
      window.removeEventListener("pointermove", wake);
      window.removeEventListener("pointerdown", wake);
      window.clearTimeout(t);
    };
  }, [phase]);

  const begin = () => {
    update({ sound: true });
    engine.unlock();
    const a = audio.current;
    if (!a || failed) {
      finish();
      return;
    }
    a.muted = false;
    a.volume = settings.volume;
    a.currentTime = 0;
    a.play().catch(() => finish());
    withTransition(() => setPhase("film"));
  };

  return (
    <section className="intro" aria-label="Introduction">
      {phase === "ready" ? (
        <>
          <div className="intro-body">
            <h1 id="intro-title" ref={h1} tabIndex={-1}>
              Listen to the Earth
            </h1>
            <button
              type="button"
              className="primary"
              aria-describedby="intro-hint"
              onClick={begin}
            >
              Begin <Icon name="arrow" size={20} />
            </button>
            <p id="intro-hint" className="intro-hint">
              <span className="sr-only">
                A short story told by the planet, with sound and subtitles.{" "}
              </span>
              <Icon name="headphones" size={16} /> Best with headphones
            </p>
          </div>
          <button type="button" className="link intro-skip" onClick={finish}>
            Skip intro
          </button>
        </>
      ) : (
        <div ref={stage} className={`film${active ? " is-active" : ""}`}>
          <h2 ref={filmHeading} tabIndex={-1} className="sr-only">
            Introduction: the Earth tells its story. Press Escape to skip it.
          </h2>
          <div className="film-stars" aria-hidden="true" />
          <div className="film-earth" aria-hidden="true">
            <EarthGlobe spinning={!reducedMotion && !paused} />
          </div>
          <p className="film-line" aria-hidden="true">
            {line ? <span key={line}>{line}</span> : null}
          </p>
          <div className="film-controls">
            <button type="button" className="ghost" onClick={toggle}>
              {paused ? "Resume narration" : "Pause narration"}
            </button>
            <button type="button" className="ghost" onClick={finish}>
              Skip introduction
            </button>
          </div>
          <div className="sr-only">
            <h3>What the Earth says</h3>
            {NARRATION.map((l) => (
              <p key={l}>{l}</p>
            ))}
          </div>
        </div>
      )}
      <audio
        ref={audio}
        src="intro/narration.m4a"
        preload="auto"
        onPlay={() => setPaused(false)}
        onPause={() => setPaused(true)}
        onEnded={() => {
          endTimer.current = window.setTimeout(
            finish,
            reducedMotion ? 0 : 1500,
          );
        }}
        onError={() => {
          setFailed(true);
          if (phase === "film") finish();
        }}
        onTimeUpdate={(e) => {
          const t = e.currentTarget.currentTime;
          setLine(cues.find((c) => t >= c.start && t < c.end)?.text ?? "");
        }}
      >
        <track
          kind="captions"
          src="intro/narration.vtt"
          srcLang="en"
          label="English"
          default
        />
      </audio>
    </section>
  );
}
