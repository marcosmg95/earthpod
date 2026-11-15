import { useEffect, useRef, useState, type CSSProperties } from "react";
import { withTransition } from "../a11y/transition";
import { useShortcuts } from "../a11y/useShortcuts";
import { CHAPTERS, type Chapter } from "../chapters";
import { Captions } from "../components/Captions";
import { EarthGlobe } from "../components/EarthGlobe";
import { FrameView } from "../components/FrameView";
import { Icon } from "../components/Icon";
import { Player } from "../components/Player";
import { SceneLink } from "../components/SceneLink";
import { Transcript } from "../components/Transcript";
import { useTrack } from "../data/useTrack";
import { engine, useEngine } from "../engine/store";
import { useSettings } from "../settings/context";

type Phase = "title" | "scene" | "between" | "end";

const delay = (s: number): CSSProperties =>
  ({ "--d": `${s}s` }) as CSSProperties;

export function ChapterPage({
  chapterId,
  trackId,
}: {
  chapterId: string;
  trackId?: string;
}) {
  const chapter = CHAPTERS.find((c) => c.id === chapterId);
  const firstScene = Math.max(
    0,
    chapter?.tracks.findIndex((t) => t.id === trackId) ?? 0,
  );
  const [scene, setScene] = useState(firstScene);
  const [phase, setPhase] = useState<Phase>("title");
  const [globeTurning, setGlobeTurning] = useState(true);
  const view = chapter?.tracks[scene];
  const { track, error } = useTrack(view ?? null);
  const { trackKey, frame, ended } = useEngine();
  const { settings, reducedMotion } = useSettings();
  const heading = useRef<HTMLHeadingElement>(null);
  const playerRef = useRef<HTMLDivElement>(null);
  const playWhenLoaded = useRef(false);
  const loaded = track && view && trackKey === view.dir ? track : null;
  const total = chapter?.tracks.length ?? 0;

  useEffect(() => {
    if (track && view) engine.load(view.dir, track);
  }, [track, view]);

  useEffect(() => () => engine.stop(), []);

  useEffect(() => {
    document.title = chapter
      ? `${chapter.short} · EarthPod`
      : "Chapter not found · EarthPod";
    heading.current?.focus();
  }, [phase, scene, chapter]);

  useEffect(() => {
    const t = window.setTimeout(() => setGlobeTurning(false), 4500);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (phase === "scene" && loaded && playWhenLoaded.current) {
      playWhenLoaded.current = false;
      engine.play();
    }
  }, [phase, loaded]);

  useEffect(() => {
    if (phase !== "scene" || !loaded || !ended) return;
    withTransition(() => setPhase(scene + 1 < total ? "between" : "end"));
  }, [phase, loaded, ended, scene, total]);

  useShortcuts(
    playerRef,
    phase === "scene" && loaded !== null && settings.shortcuts,
  );

  if (!chapter || !view) {
    return (
      <section className="page" aria-labelledby="nf-title">
        <h1 id="nf-title" ref={heading} tabIndex={-1}>
          Chapter not found
        </h1>
        <p>
          <SceneLink href="/record">See all chapters</SceneLink>
        </p>
      </section>
    );
  }

  const start = () => {
    if (!loaded) return;
    engine.unlock();
    if (engine.get().ended) engine.seekTime(0, false);
    engine.play();
    withTransition(() => setPhase("scene"));
  };

  const nextScene = () => {
    playWhenLoaded.current = true;
    withTransition(() => {
      setScene((s) => s + 1);
      setPhase("scene");
    });
  };

  const watchAgain = () => {
    engine.stop();
    withTransition(() => {
      setScene(0);
      setPhase("title");
    });
  };

  const nextChapter = CHAPTERS[
    CHAPTERS.findIndex((c) => c.id === chapter.id) + 1
  ] as Chapter | undefined;
  const next = nextChapter
    ? { href: `/${nextChapter.id}`, label: `Next: ${nextChapter.short}` }
    : { href: "/record", label: "See all chapters" };

  if (phase === "title") {
    return (
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
            <span className="sr-only">Chapter </span>
            {chapter.num}
            <span className="sr-only">: </span>
          </span>
          {chapter.title}
        </h1>
        <p id="title-logline" className="logline reveal" style={delay(0.8)}>
          {chapter.logline}
        </p>
        {error ? (
          <p role="alert" className="notice reveal" style={delay(1.2)}>
            {view.label} is not ready yet. {error}
          </p>
        ) : (
          <button
            type="button"
            className="primary reveal"
            style={delay(1.2)}
            aria-disabled={!loaded}
            aria-describedby="title-logline"
            onClick={start}
          >
            {loaded ? (
              <>
                Start <Icon name="play" size={18} />
              </>
            ) : (
              "Loading…"
            )}
          </button>
        )}
      </section>
    );
  }

  if (phase === "between") {
    const upcoming = chapter.tracks[scene + 1];
    return (
      <section className="interlude" aria-labelledby="between-heading">
        <h1
          id="between-heading"
          ref={heading}
          tabIndex={-1}
          className="reveal"
          style={delay(0.2)}
        >
          <span className="sr-only">
            Scene {scene + 1} of {total} complete.{" "}
          </span>
          Next: {upcoming.label}
        </h1>
        <button
          type="button"
          className="primary reveal"
          style={delay(0.6)}
          onClick={nextScene}
        >
          Play <Icon name="play" size={18} />
        </button>
        <button
          type="button"
          className="link reveal"
          style={delay(0.8)}
          onClick={() => withTransition(() => setPhase("end"))}
        >
          Skip to the end of the chapter
        </button>
      </section>
    );
  }

  if (phase === "end") {
    const sources = [
      ...new Set(chapter.tracks.map((t) => t.source.replace(/^NASA /, ""))),
    ].join(", ");
    return (
      <section className="end-card" aria-labelledby="end-heading">
        <h1
          id="end-heading"
          ref={heading}
          tabIndex={-1}
          className="reveal"
          style={delay(0.2)}
        >
          <span className="sr-only">End of chapter {chapter.num}: </span>
          {chapter.title}
        </h1>
        <div className="end-actions reveal" style={delay(0.6)}>
          <SceneLink href={next.href} className="primary">
            {next.label} <Icon name="arrow" size={18} />
          </SceneLink>
          <button type="button" className="ghost" onClick={watchAgain}>
            Watch again
          </button>
        </div>
        <p className="credits reveal" style={delay(0.9)}>
          Images: NASA’s Scientific Visualization Studio ({sources}). Sound:
          CCLab. Not endorsed by NASA.
        </p>
      </section>
    );
  }

  return (
    <section className="scene" aria-labelledby="scene-heading">
      <h1 id="scene-heading" ref={heading} tabIndex={-1} className="sr-only">
        Scene {scene + 1} of {total}: {view.label}
      </h1>
      {error && (
        <div className="scene-controls">
          <p role="alert" className="notice">
            {view.label} is not ready yet. {error}
          </p>
          <button
            type="button"
            className="ghost"
            onClick={() => withTransition(() => setPhase("end"))}
          >
            Go to the end of the chapter
          </button>
        </div>
      )}
      {!error && !loaded && (
        <p role="status" className="notice scene-controls">
          Loading {view.label}…
        </p>
      )}
      {loaded && (
        <>
          <div className="screen">
            <FrameView track={loaded} frame={frame}>
              <p className="slate" aria-hidden="true">
                <span>Scene {scene + 1}</span>
                {view.label}
              </p>
              <Captions track={loaded} />
            </FrameView>
          </div>
          <div ref={playerRef} className="scene-controls">
            <Player track={loaded}>
              <Transcript track={loaded} />
            </Player>
          </div>
          {loaded.about && (
            <details className="scene-controls scene-about">
              <summary>About this visualization, from NASA</summary>
              {loaded.about.split(/\n+/).map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </details>
          )}
        </>
      )}
    </section>
  );
}
