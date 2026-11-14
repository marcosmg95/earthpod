import { createContext, useContext } from "react";

export type MotionPref = "system" | "reduce" | "full";

export interface Settings {
  sound: boolean;
  volume: number;
  rate: number;
  shortcuts: boolean;
  motion: MotionPref;
}

export const DEFAULT_SETTINGS: Settings = {
  sound: true,
  volume: 0.8,
  rate: 1,
  shortcuts: true,
  motion: "system",
};

export interface SettingsApi {
  settings: Settings;
  reducedMotion: boolean;
  update: (patch: Partial<Settings>) => void;
}

export const SettingsContext = createContext<SettingsApi | null>(null);

export function useSettings(): SettingsApi {
  const api = useContext(SettingsContext);
  if (!api)
    throw new Error("useSettings must be used inside <SettingsProvider>");
  return api;
}
