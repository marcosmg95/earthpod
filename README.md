# EarthPod — The Earth Information Jukebox

**CCLab · NASA Space Apps Challenge 2026 · Barcelona (42 Barcelona, 14–15 Nov)**

Challenge: pair NASA Earth Information Center visuals with sonifications, with accessibility as a core theme.

EarthPod lets you _listen_ to NASA Earth imagery. The Earth narrates a short intro, teaches you its instruments,
then plays chapters where NASA visualizations and their sonifications run together. It is built to work fully
with a screen reader, a keyboard, captions and reduced motion, not as an afterthought.

**Live:** https://earthpod.earth

## How it works

1. **Data team (`backend/`)**: turns NASA SVS visualizations into sound. Every region of the Earth has its own
   instrument; when it comes into view, you hear it. Output: a `.mp4` + `.wav` (+ `.vtt` descriptions) per scene.
2. **Web app (`frontend/web/`)**: plays them in sync as cinematic chapters, with a sound chart, captions,
   a transcript and spoken descriptions.

| Chapter                 | Data                                                    |
| ----------------------- | ------------------------------------------------------- |
| 00 How to listen        | The instrument samples                                  |
| 01 The breathing planet | NASA SVS 5196: global CO₂ (DYAMOND model), Jan–Mar 2020 |
| 02 Night lights         | NASA SVS 5313: Black Marble night lights                |

## Repository layout

```
backend/            Python (uv): sonification, scripts, tests        -> backend/README.md
frontend/web/       The web app (Vite + React + TypeScript)          -> frontend/web/README.md
infra/              Dockerfile + nginx config for the deployed site
config/deploy.yml   Kamal deploy config
docs/               Research, design, task plan, submission checklist, AI-use log
```

## Quick start

```bash
# web app
cd frontend/web
npm install
npm run dev                 # http://localhost:5173

# backend
cd backend
uv sync
uv run python -m unittest discover -s tests -v
```

## Deploy (CI/CD)

Every push and PR runs `.github/workflows/ci.yml`: backend tests, plus lint, format check and build of the web app.
A push to `main` that passes both deploys to **https://earthpod.earth** with Kamal: `infra/Dockerfile` builds
`frontend/web` and serves it with nginx (`infra/nginx.conf`); the image goes to ghcr.io and kamal-proxy handles TLS.
Repo secret needed: `VPS8_SSH_KEY`.

Test the production image locally (from the repo root):

```bash
docker build -f infra/Dockerfile -t earthpod . && docker run --rm -p 8080:80 earthpod   # http://localhost:8080
```

## Docs

| File                            | Content                                      |
| ------------------------------- | -------------------------------------------- |
| docs/01-research-summary.md     | Key findings from the early investigation    |
| docs/02-data-sources.md         | EIC/SVS visualizations, licensing            |
| docs/03-sonification-design.md  | Mapping table, musicality rules, prior art   |
| docs/04-accessibility.md        | WCAG, keyboard model, ARIA, user testing     |
| docs/05-concepts.md             | Concept directions and the MVP               |
| docs/06-task-plan.md            | Task plan until submission                   |
| docs/07-submission-checklist.md | Submission and judging checklist             |
| docs/ai-use-log.md              | Log of AI tool use (required for submission) |

## Credits

Images: NASA Scientific Visualization Studio (SVS 5196, SVS 5313). Public domain. Not endorsed by NASA.
Narration voice: Kokoro-82M (Apache-2.0). Map data: Natural Earth (public domain).
