# EarthPod web app

Vite + React 19 + TypeScript. Plays NASA Earth visualizations with their sonifications, accessible first.
Live at https://earthpod.earth.

## Run

```bash
npm install
npm run dev          # http://localhost:5173
npm run lint         # ESLint: typed rules, jsx-a11y strict
npm run build        # type-check + build -> dist/
npm run test:e2e     # Playwright + axe end-to-end tests (builds and serves the app itself)
npx prettier --write src
```

Use Node 22. The first time you run the end-to-end tests, install the browser with `npx playwright install chromium`.
Prettier formats on save in VS Code (`frontend/.vscode/settings.json`; open the `frontend` folder, or copy the
settings to the folder you open).

## The experience

`#/` intro film → `#/listen` 00 How to listen → `#/co2` 01 → `#/nightlights` 02 → `#/aerosols` 03 → `#/record` · `#/accessibility`

- **Intro**: the Earth tells its story (narration with captions). Begin needs a click, because browsers block sound
  until then. Escape or "Skip intro" goes straight to 00.
- **00 How to listen**: the sounds of each chapter. For 01, each continent's button sits around the globe, and the
  globe turns to that continent while its sample plays; 02 and 03 have a list of samples made from their own data.
- **Chapters**: title card → scenes → end card. Each scene plays a muted video kept in step with its sound (03 is a
  still map, SVS 5669, shown as a video of a line scanning it west → east), with a
  sound chart you can drag, captions, an Options panel (speed, Describe, chart key, transcript) and NASA's own
  text about the visualization.
- **Accessibility**: the accessibility statement.

## Where things are

```
src/
  routes/       Intro, HowToListen, ChapterPage, Record, Accessibility
  components/   Header (menu), Player, SoundChart, FrameView (video sync), Captions, Transcript,
                EarthGlobe, SettingsPanel, SceneLink, Icon
  engine/       Sound: media player, store, waveform (the only place allowed to touch Web Audio)
  a11y/         Announcements (throttled live region), keyboard shortcuts, view transitions
  data/         Track loading (zod), WebVTT parser, time labels
  settings/     Sound, volume, speed, shortcuts, motion (saved in localStorage)
  chapters.ts   Chapters and their scenes
  samples.ts    Instrument samples for 00
public/
  data/<chapter>/<name>.mp4 | .wav | .vtt | .peaks.json   one scene
  data/<chapter>/svs<id>_nasa_description.txt              NASA's text for the visualization
  data/samples/                                            instrument samples (+ .peaks.json)
  intro/narration.m4a + .vtt                               intro narration
e2e/            Playwright + axe tests
scripts/
  make_narration_kokoro.py   intro voice (Kokoro text-to-speech)
  make_narration.py          the same with macOS `say` (fallback)
  make_peaks.py              waveform files for the sound chart
```

## Adding a scene

1. Put the scene's files in `public/data/<chapter>/`, all with the same name:
   - `<name>.mp4`: H.264, yuv420p, no audio, ≤ 1920 px wide, < 50 MB;
   - `<name>.wav`: the sonification, the same length as the video;
   - `<name>.vtt`: the descriptions (see below).
2. Make its waveform file, so the sound chart appears at once: `python scripts/make_peaks.py`
   (needs ffmpeg and numpy). Commit the `.peaks.json` it writes.
3. Add it to the chapter's `tracks` in `src/chapters.ts`:
   ```ts
   {
     id: "west-europe",                       // used in the URL: #/nightlights/west-europe
     label: "Western Europe",                 // read out and shown on the scene's slate
     dir: "nightlights/<name>",               // path under public/data/, without the extension
     source: "NASA SVS 5313",
     about: "nightlights/svs5313_nasa_description", // NASA's text, without .txt (optional)
     start: "2012-01-01", end: "2023-12-31",  // dates for the timeline (optional; otherwise minutes:seconds)
     // scan: { from: -180, to: 180 },        // still scenes: the timeline shows the scan line's longitude instead
   }
   ```

To convert a video that does not play:

```bash
ffmpeg -i in.mp4 -c:v libx264 -crf 23 -preset veryfast -pix_fmt yuv420p -vf "scale='min(1920,iw)':-2" -an -movflags +faststart out.mp4
```

### Descriptions (`.vtt`) and NASA text (`.txt`)

The `.vtt` file is what people who cannot see the screen rely on. Its cues are announced while the scene plays,
read out by Describe (D) and listed in the transcript. Write one short cue per key moment, one sentence each:
the date, what is on screen, each continent coming into view and its instrument, big changes. Long cues cover the
picture and are read over the music, so split them.

```
WEBVTT

00:00:00.000 --> 00:00:04.000
14 January 2020. Asia and Australia face us; CO₂ glows orange-red over eastern China.

00:00:09.500 --> 00:00:13.000
Africa comes into view: flute for Europe, marimba for Africa.
```

The `.txt` file is NASA's text about the visualization, shown under the player as "About this visualization".
Plain text, one paragraph per line. Both files are optional: without them, those features stay hidden.

## Intro narration

```bash
brew install espeak-ng uv
uv venv --python 3.12 .venv-tts && source .venv-tts/bin/activate
uv pip install "kokoro>=0.9.4" soundfile numpy
python scripts/make_narration_kokoro.py --voice bf_emma --lang b --speed 0.82 --pitch -2.5 --room empty
```

This writes `public/intro/narration.m4a` and `.vtt`. If you change the lines, keep `LINES` in the script and
`NARRATION` in `src/routes/Intro.tsx` the same.

## Accessibility rules (keep them)

- No autoplay: sound starts only after a click (WCAG 1.4.2).
- Nothing moves for more than 5 s without a way to pause it; `data-motion="reduce"` stops all motion (2.2.2).
- Every page and phase has one `h1`, which takes focus; announcements go through `a11y/announce.ts`.
- Keyboard shortcuts work only inside the player and can be turned off in Settings (2.1.4).
- Speech has captions; sonifications have descriptions (`.vtt`) and a transcript.
- Targets are at least 44 px; text contrast is at least 4.5:1; check forced-colors mode and 400% zoom.
- ESLint blocks `AudioContext`, `speechSynthesis`, `autoPlay` and `aria-live` outside their modules.
  Don't disable those rules.

`npm run test:e2e` checks most of this automatically (axe on every screen, focus, keyboard, menu, reduced motion,
320 px reflow). Before merging, also try the keyboard only, VoiceOver (Cmd+F5) and Reduce motion yourself.

## Deploy

CI runs lint, the format check, the build and the end-to-end tests on every push and pull request. Merging to `main`
deploys automatically (see the root README). To check the production image locally, from the repo root:

```bash
docker build -f infra/Dockerfile -t earthpod . && docker run --rm -p 8080:80 earthpod   # http://localhost:8080
```
