import {
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { engine } from "../engine/store";
import {
  DEFAULT_SETTINGS,
  SettingsContext,
  type Settings,
  type SettingsApi,
} from "./context";

const KEY = "ej:settings";
const REDUCE = "(prefers-reduced-motion: reduce)";

function readSettings(): Settings {
  try {
    const raw = localStorage.getItem(KEY);
    return raw
      ? { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<Settings>) }
      : DEFAULT_SETTINGS;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function subscribeMotion(cb: () => void): () => void {
  const m = matchMedia(REDUCE);
  m.addEventListener("change", cb);
  return () => m.removeEventListener("change", cb);
}
const systemReduced = (): boolean => matchMedia(REDUCE).matches;

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState(readSettings);
  const system = useSyncExternalStore(subscribeMotion, systemReduced);
  const reducedMotion =
    settings.motion === "system" ? system : settings.motion === "reduce";

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(settings));
    } catch {
      // private mode: settings last for this visit only
    }
    engine.setVolume(settings.sound ? settings.volume : 0);
    engine.setRate(settings.rate);
    engine.setDescriptions(settings.captions);
  }, [settings]);

  useEffect(() => {
    document.documentElement.dataset.motion = reducedMotion ? "reduce" : "full";
  }, [reducedMotion]);

  const api = useMemo<SettingsApi>(
    () => ({
      settings,
      reducedMotion,
      update: (patch) => setSettings((s) => ({ ...s, ...patch })),
    }),
    [settings, reducedMotion],
  );

  return <SettingsContext value={api}>{children}</SettingsContext>;
}
