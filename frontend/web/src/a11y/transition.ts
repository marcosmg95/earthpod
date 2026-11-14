import { flushSync } from "react-dom";

/**
 * Run a UI change as a cross-fade through black (View Transitions API).
 * With reduced motion, or in browsers without the API, the change happens at once.
 */
export function withTransition(update: () => void): void {
  const reduce = document.documentElement.dataset.motion === "reduce";
  if (reduce || typeof document.startViewTransition !== "function") {
    update();
    return;
  }
  document.startViewTransition(() => {
    flushSync(update);
  });
}
