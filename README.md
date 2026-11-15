# EarthPod — The Earth Information Jukebox

**NASA Space Apps Challenge 2026 · Barcelona**

EarthPod is a browser-based listening experience for NASA Earth imagery, designed for keyboard and assistive-technology use. It pairs selected NASA Scientific Visualization Studio (SVS) visualizations with original sonifications, introductory captions, and time-coded descriptions and transcripts where available. Sound starts only after a user action.

**Try it:** [earthpod.earth](https://earthpod.earth)

## The experience

Start with **How to listen**, which introduces the sounds and controls. Then explore:

| Chapter | Source and period | What you hear |
| --- | --- | --- |
| The breathing planet | NASA SVS 5196, global CO₂ model visualization, 14 January–2 March 2020 | A layered heart-and-lungs metaphor follows patterns measured from the visualization. |
| The night lights | NASA SVS 5313, Earth at night, 2012–2023 | A musical journey through the yearly maps and the visualization’s purple/orange change map. |

These sonifications describe patterns in the source imagery; they are not direct readings of calibrated CO₂ concentrations or night-light radiance. EarthPod also includes a record of the project and an accessibility statement in the app.

## Run locally

The production experience is the static web app in `frontend/web/`. Requirements: Node.js 22 or compatible and npm.

```powershell
cd frontend\web
npm ci
npm run dev
```

Open the local URL printed by Vite. To run the production build and checks:

```powershell
npm run build
npm run lint
npm run test:e2e
```

The Playwright end-to-end suite builds and serves the production app before running its browser tests.

## Project structure

| Path | Purpose |
| --- | --- |
| `frontend/web/` | Production web experience (React, TypeScript, Vite) |
| `backend/` | Python data preparation, sonification research tools, SVS explorer, and tests |
| `backend/data/derived/` | Small, committed measurements used by backend tools |
| `docs/` | Research, data-source, accessibility, delivery, and AI-use notes |
| `infra/` and `config/deploy.yml` | Production image and Kamal deployment configuration |

The backend's GISTEMP and legacy player scripts are retained for reproducibility and experimentation. They are separate from the two chapters in the production web app. See [backend/README.md](backend/README.md) for backend setup, data reproduction, and limitations.

## Backend checks

The backend uses [uv](https://docs.astral.sh/uv/). From `backend/`:

```powershell
uv sync
uv run python -m unittest discover -s tests -v
```

Some data-reproduction commands download large NASA source movies. The downloadable raw inputs are gitignored; the checked-in derived files and instructions are documented in [backend/data/README.md](backend/data/README.md).

## Deployment

The Docker image builds `frontend/web/` and serves its static output with nginx. Pushes to `main` are deployed by the repository's configured CI/Kamal workflow when its checks and deployment credentials are available. See [infra/Dockerfile](infra/Dockerfile), [infra/nginx.conf](infra/nginx.conf), and [config/deploy.yml](config/deploy.yml). The deployed site is [earthpod.earth](https://earthpod.earth).

## Accessibility and source credit

The app's [accessibility statement](https://earthpod.earth/#/accessibility) describes the implemented controls, the checks performed, and known limitations. The app was built for keyboard and assistive-technology use, but has not had an independent accessibility audit.

Imagery: NASA Scientific Visualization Studio (SVS 5196 and SVS 5313). Data and visualizations remain credited to their sources. EarthPod is not endorsed by NASA. See [docs/02-data-sources.md](docs/02-data-sources.md) for source details and [docs/ai-use-log.md](docs/ai-use-log.md) for AI-use disclosure.

## License

- **Code** (everything in `backend/`, `frontend/`, `infra/`, `config/` and the scripts): [MIT](LICENSE).
- **Original content** (documentation in `docs/`, the generated sonifications and narration audio, and the derived
  data in `backend/data/derived/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Please credit "EarthPod".
- **NASA data, imagery and visualizations** (SVS movies and frames, GISTEMP, Black Marble and other sources) are not
  covered by these licenses. They stay under their original terms; see the
  [NASA Images and Media Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) and
  [docs/02-data-sources.md](docs/02-data-sources.md). EarthPod is not endorsed by NASA.
- Third-party libraries and the Kokoro-82M voice model (Apache-2.0) keep their own licenses.

## Documentation

| Document | What it covers |
| --- | --- |
| [docs/01-research-summary.md](docs/01-research-summary.md) | Project context and how the initial research informed the delivered scope |
| [docs/02-data-sources.md](docs/02-data-sources.md) | NASA sources, what the app uses, and backend-only experiments |
| [docs/03-sonification-design.md](docs/03-sonification-design.md) | The shipped chapter mappings and interpretive limits |
| [docs/04-accessibility.md](docs/04-accessibility.md) | Implemented accessibility behavior and known gaps |
| [docs/05-concepts.md](docs/05-concepts.md) | Early concepts and which ideas became the product |
| [docs/06-task-plan.md](docs/06-task-plan.md) | Delivery closeout and project handoff |
| [docs/07-submission-checklist.md](docs/07-submission-checklist.md) | Final handoff checks |
| [docs/ai-use-log.md](docs/ai-use-log.md) | Disclosure of AI assistance |
