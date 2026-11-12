# 04 — Accessibility

## Must-haves
- No autoplay. WCAG 2.2 SC 1.4.2: audio only starts on user action; Play/Pause and volume first in tab order.
- Full keyboard operation with native `<button>` / `<input type="range">`, `aria-label`, `aria-valuetext` (e.g. "1998, +0.61 °C"), visible focus.
- `aria-live="polite"` region: year, value, one-line description per step. Throttled; never every frame during playback.
- Meaningful `alt` on each frame; full text transcript per track.
- Orientation intro (~20 s) explaining the mapping; reference tone for baseline 0 °C.
- Captions + audio description in the demo video.
- High contrast, `prefers-reduced-motion`, mono-compatible mix.

## Keyboard model (draft)
| Key | Action |
|---|---|
| Space | Play / pause |
| ← / → | Previous / next year |
| Shift + ← / → | Jump a decade |
| ↑ / ↓ | Volume (or latitude band) |
| D | Speak/announce description |
| R | Play reference tone |
| 1–5 | Solo a layer |
| B | Toggle Planet ↔ Barcelona |

## Optional
- Web Speech API narration as opt-in (don't fight the user's screen reader).
- Haptics: `navigator.vibrate()` — Chromium/Android only, after user tap; never on iOS Safari. Feature-detect; e.g. pulse on record years.

## User testing
- Ask the 42 Barcelona organizers and/or ONCE for a blind/low-vision tester for ~20 min on Sunday morning.
- Test with NVDA (Windows) and VoiceOver (macOS/iOS) at least once before.
- Capture one quote (with permission) for the pitch.
