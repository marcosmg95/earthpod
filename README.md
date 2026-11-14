# CCLab — The Earth Information Jukebox (NASA Space Apps 2026, Barcelona)

Event: 14–15 Nov 2026, 42 Barcelona. Challenge: pair NASA Earth Information Center (EIC) visual frames with real-time sonifications, with accessibility as a core theme.

## Working thesis
A browser-based jukebox built for screen-reader users first. Sound is driven by real measured data (GISTEMP), synced to NASA SVS frames, with a "Listen to Barcelona" local track.
Differentiators: scientifically honest mapping, real testing with a blind/low-vision user, local story.

## Repository layout
```
backend/     Python (uv): src/jukebox/ package, apps/ (Streamlit), scripts/, tests/, data/  -> backend/README.md
frontend/    Static web apps: arcade/ (the experience) and player/ (accessible GISTEMP player) -> frontend/README.md
docs/        Research, design, task plan, submission checklist, AI-use log
```

## Quick start (Windows, from the repo root)
```powershell
cd backend; uv sync                                # creates backend\.venv from pyproject.toml + uv.lock
uv run python -m unittest discover -s tests -v
uv run streamlit run apps\svs_explorer.py          # browse NASA SVS pages by id
cd ..\frontend\arcade; python -m http.server 8000  # the arcade: open http://localhost:8000
```
Large inputs (`backend/data/raw`, ~180 MB) and generated outputs (`backend/out`, `frontend/player/frames`) are not
committed; `backend/data/download_data.ps1` and the PoC scripts recreate them (see backend/README.md).

> If the official rules (published Fri 13 Nov) require code to be written during the event, treat the code here as
> reference only and rewrite it there.

## Docs
| File | Content |
|---|---|
| docs/01-research-summary.md | Key findings from the early investigation |
| docs/02-data-sources.md | EIC/SVS visualizations, GISTEMP, GIBS, licensing, colormap inversion |
| docs/03-sonification-design.md | Mapping table, musicality rules, prior art |
| docs/04-accessibility.md | WCAG, keyboard model, ARIA, haptics, user testing |
| docs/05-concepts.md | Concept directions and the recommended MVP |
| docs/06-task-plan.md | Task plan from today until submission |
| docs/07-submission-checklist.md | Submission and judging checklist |
| docs/ai-use-log.md | Log of AI tool use (required for submission) |

## Open questions for the team
- Final name (ideas: "Escolta la Terra", "Terra Cançó")
- Roles: who owns data, audio engine, UI/accessibility, story/pitch/video
- Do official rules forbid pre-written code? (check Fri 13 Nov)

Data: GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA GISS.
Frames and images: NASA Scientific Visualization Studio (SVS 5450) and other public-domain NASA imagery. Not endorsed by NASA.
