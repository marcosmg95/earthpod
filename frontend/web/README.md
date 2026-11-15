# EarthPod web app

Vite + React 19 + TypeScript. Plays NASA Earth visualizations with their sonifications, accessible first.

## Run
```bash
npm install
npm run dev        # http://localhost:5173
npm run lint       # ESLint (jsx-a11y strict, typed rules)
npm run build      # -> dist/
npx prettier --write src
```
Use Node 22. Prettier formats on save in VS Code (see `.vscode/settings.json`).

## The experience
`/` intro film → `#/listen` 00 How to listen → `#/co2` 01 → `#/night` 02 → `#/record` · `#/explore`

- **Intro**: the Earth tells its story (narration + captions). Begin needs a click, because browsers block sound until then.
- **00 How to listen**: each instrument sample; the globe turns to the continent it stands for.
- **Chapters**: title card → scenes → end card. Each scene plays a muted video synced to its sound,
  with a sound chart you can drag, captions and a transcript.

## Where things are
```
src/
  routes/       Intro, HowToListen, ChapterPage, Record
  components/   Header (menu), Player, SoundChart, FrameView (video sync), Captions, Transcript, EarthGlobe
  engine/       Audio: media player, store, waveform analysis, probe tone (the only place allowed to touch Web Audio)
  a11y/         Announcements (live region), shortcuts, view transitions
  data/         Track loading (zod schema), WebVTT parser, time labels
  settings/     Sound, volume, speed, shortcuts, motion (saved in localStorage)
  chapters.ts   Chapters and their scenes
  samples.ts    Instrument samples for 00
public/
  data/<chapter>/<name>.mp4 | .wav | .vtt    scenes from the data team
  data/samples/                               instrument samples
  intro/narration.m4a + .vtt                  intro narration
scripts/        make_narration_kokoro.py (intro voice), make_mock_track.py
```

## Adding a scene
1. The data team puts `<name>.mp4`, `<name>.wav` and, ideally, `<name>.vtt` in `public/data/<chapter>/`, with the same name.
   - Video: H.264, yuv420p, no audio, ≤ 1920 px wide, < 50 MB.
   - Descriptions: one short cue per key moment, including when each continent comes into view.
2. Add it to the chapter's `tracks` in `src/chapters.ts`:
   ```ts
   { id: "west-europe", label: "Western Europe", dir: "nightlights/<name>",
     source: "NASA SVS 5313", start: "2020-01-01", end: "2020-03-31", burnedInTime: true }
   ```
   `dir` is the path under `public/data/` without the extension. Set `burnedInTime: true` if the video already shows the date.

To convert a video that does not play:
```bash
ffmpeg -i in.mp4 -c:v libx264 -crf 23 -preset veryfast -pix_fmt yuv420p -vf "scale='min(1920,iw)':-2" -an -movflags +faststart out.mp4
```

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
- Every page or phase moves focus to its heading; announcements go through `a11y/announce.ts`.
- Keyboard shortcuts work only inside the player and can be turned off in settings (2.1.4).
- Speech has captions; sonifications have descriptions (`.vtt`) and a transcript.
- Targets are at least 44 px; text contrast is at least 4.5:1; check forced-colors mode.
- ESLint blocks `AudioContext`, `speechSynthesis`, `autoPlay` and `aria-live` outside their modules. Don't disable those rules.

Test with the keyboard only, VoiceOver (Cmd+F5) and Reduce motion on before merging.

## Deploy
Merging to `main` deploys automatically (see the root README). To check the production build locally, from the repo root:
```bash
docker build -f infra/Dockerfile -t earthpod . && docker run --rm -p 8080:80 earthpod
```