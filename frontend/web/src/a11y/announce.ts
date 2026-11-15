import { announce } from "@react-aria/live-announcer";

let last = 0;
let ducker: ((seconds: number) => void) | null = null;

export function setDucker(fn: (seconds: number) => void): void {
  ducker = fn;
}

export function say(
  text: string,
  { force = false }: { force?: boolean } = {},
): void {
  const now = performance.now();
  if (!force && now - last < 1500) return;
  last = now;
  announce(text, "polite");
  ducker?.(Math.min(4, 0.8 + text.length * 0.06));
}
