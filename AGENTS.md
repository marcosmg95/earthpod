# AGENTS.md — instructions for AI coding agents (Claude Code, Codex, Copilot…)

## Git workflow: trunk-based, main only
- Commit directly to `main`. Do not create feature branches or PRs unless a human asks for one.
- Keep commits small and self-contained; `main` should always work (run the tests before committing).
- Pull/rebase before pushing (`git pull --rebase`) so history stays linear; never force-push `main`.

## Before committing
```powershell
cd backend; uv run python -m unittest discover -s tests -v
```
**Keep the AI-use log updated (hackathon requirement).** Space Apps requires disclosing where and how AI was used.
In the same commit as your change, add a row to `docs/ai-use-log.md` (date, tool, what it was used for, who, human review).
The submission's AI-use statement is built from it (`docs/07-submission-checklist.md`).

If you changed `backend/src/jukebox/mapping.py` or data loaders, re-run `uv run python scripts\poc2_export_tracks.py`
(from `backend/`) and check that the existing tracks in `frontend/player/tracks.json` are unchanged unless that was the intent.

## Python environment: uv
- The backend is a uv project: `backend/pyproject.toml` + `backend/uv.lock` (commit it); package code in `backend/src/jukebox/`.
- Add deps with `uv add <pkg>` (`--optional netcdf|blackmarble` for PoC-only deps, `--group explorer` for the Streamlit app).
- No `requirements.txt`, no `sys.path` hacks: scripts/tests/apps `import jukebox` from the installed package.

## Never commit
- Secrets: `EARTHDATA_TOKEN` lives in the user environment only.
- Large inputs/outputs: `backend/data/raw/` (GBs of NASA files), `backend/out/`, `frontend/player/frames/` (gitignored).
- Small derived results in `backend/data/derived/` *are* committed so the app works without downloads.

## Where things are
- Repo overview: `README.md`; backend and how to reproduce every dataset: `backend/README.md`; data notes: `backend/data/README.md`.
- Windows quirks (Smart App Control blocks some DLLs and the `.venv\Scripts\*.exe` launchers, pandas pinned < 3):
  see `backend/README.md` → Windows notes. Run tools as `uv run python -m <tool>`; VS Code entry points are in `.vscode/launch.json`.
- Sonification scripts (audio played in sync with an SVS movie in the explorer's Sonify tab): one `.py` per script in
  `backend/sonifications/` with `TITLE`, `DESCRIPTION` and `render(ctx) -> stereo np.ndarray`. Contract: `backend/src/jukebox/sonify.py`
  docstring + `backend/README.md` → Sonification scripts; template: `gistemp_lead.py`.
  Reuse `jukebox.mapping` / `jukebox.synth` (via `ctx.notes_from_series`, `ctx.render_notes`) instead of new synth code,
  and name the data source in `DESCRIPTION`.
- Accessibility is a core requirement: keyboard-only, screen-reader live regions, no autoplay (see `docs/04-accessibility.md`).
- Credit NASA sources in captions and `source` fields; never imply NASA endorsement.
