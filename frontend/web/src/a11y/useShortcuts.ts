import { useEffect, type RefObject } from "react";
import { engine } from "../engine/store";

function isTyping(t: EventTarget | null): boolean {
  if (t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement)
    return true;
  return (
    t instanceof HTMLInputElement &&
    !["range", "checkbox", "radio", "button"].includes(t.type)
  );
}

function activatesOnSpace(t: EventTarget | null): boolean {
  if (t instanceof HTMLButtonElement || t instanceof HTMLAnchorElement)
    return true;
  if (t instanceof HTMLInputElement)
    return t.type === "checkbox" || t.type === "radio";
  return t instanceof HTMLElement && t.tagName === "SUMMARY";
}

export function useShortcuts(
  ref: RefObject<HTMLElement | null>,
  enabled: boolean,
): void {
  useEffect(() => {
    const el = ref.current;
    if (!el || !enabled) return;
    const onKey = (e: KeyboardEvent): void => {
      if (e.altKey || e.ctrlKey || e.metaKey || isTyping(e.target)) return;
      const onRange =
        e.target instanceof HTMLInputElement && e.target.type === "range";
      const key = e.key.toLowerCase();
      if (key === " ") {
        if (activatesOnSpace(e.target)) return;
        e.preventDefault();
        engine.toggle();
      } else if (key === "arrowleft" || key === "arrowright") {
        if (onRange && !e.shiftKey) return; // the slider moves itself one frame
        e.preventDefault();
        engine.step((key === "arrowright" ? 1 : -1) * (e.shiftKey ? 10 : 1));
      } else if (key === "d") {
        engine.describe();
      }
    };
    el.addEventListener("keydown", onKey);
    return () => el.removeEventListener("keydown", onKey);
  }, [ref, enabled]);
}
