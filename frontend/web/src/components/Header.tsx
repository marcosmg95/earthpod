import { useEffect, useRef, type MouseEvent } from "react";
import { Link, useLocation } from "wouter";
import { CHAPTER_NAV, MORE_NAV } from "../chapters";
import { engine } from "../engine/store";
import { useSettings } from "../settings/context";
import { Icon } from "./Icon";
import { SceneLink } from "./SceneLink";
import { SettingsPanel } from "./SettingsPanel";

export function Header() {
  const [location] = useLocation();
  const current = location.split("/")[1] ?? "";
  const { settings, update } = useSettings();
  const menu = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    if (menu.current) menu.current.open = false;
  }, [location]);

  useEffect(() => {
    const el = menu.current;
    if (!el) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || !el.open) return;
      el.open = false;
      el.querySelector("summary")?.focus();
    };
    const onPointer = (e: PointerEvent) => {
      if (el.open && e.target instanceof Node && !el.contains(e.target))
        el.open = false;
    };
    el.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      el.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, []);

  const skip = (e: MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    document.getElementById("main")?.focus();
  };

  const toggleSound = () => {
    const on = !settings.sound;
    update({ sound: on });
    if (on) engine.unlock();
  };

  return (
    <header className="site-header">
      <a className="skip" href="#main" onClick={skip}>
        Skip to content
      </a>
      <Link href="/" className="brand">
        EarthPod
      </Link>
      <details ref={menu} className="menu">
        <summary>Menu</summary>
        <div className="menu-panel">
          <nav aria-label="Chapters">
            <ol className="menu-list">
              {CHAPTER_NAV.map((n) => (
                <li key={n.id}>
                  <SceneLink href={n.href} current={n.id === current}>
                    <span className="num">{n.num}</span>
                    {n.short}
                  </SceneLink>
                </li>
              ))}
            </ol>
          </nav>
          <nav aria-label="More">
            <ul className="menu-list">
              {MORE_NAV.map((n) => (
                <li key={n.id}>
                  <SceneLink href={n.href} current={n.id === current}>
                    {n.short}
                  </SceneLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="menu-tools">
            <button
              type="button"
              className="ghost"
              aria-pressed={settings.sound}
              onClick={toggleSound}
            >
              <Icon name={settings.sound ? "sound" : "mute"} /> Sound
            </button>
            <SettingsPanel />
          </div>
        </div>
      </details>
    </header>
  );
}
