# AGENTS.md — instructions for AI coding agents (Claude Code, Codex, Copilot…)

## Git workflow: trunk-based, main only
- Commit directly to `main`. Do not create feature branches or PRs unless a human asks for one.
- Keep commits small and self-contained; `main` should always work (run the tests before committing).
- Pull/rebase before pushing (`git pull --rebase`) so history stays linear; never force-push `main`.

## Before committing
```powershell
python -m unittest discover -s backend\tests -v
```
**Keep the AI-use log updated (hackathon requirement).** Space Apps requires disclosing where and how AI was used.
In the same commit as your change, add a row to `docs/ai-use-log.md` (date, tool, what it was used for, who, human review).
The submission's AI-use statement is built from it (`docs/07-submission-checklist.md`).

If you changed `backend/jukebox/mapping.py` or data loaders, re-run `python backend\scripts\poc2_export_tracks.py`
and check that the existing tracks in `frontend/player/tracks.json` are unchanged unless that was the intent.

## Never commit
- Secrets: `EARTHDATA_TOKEN` lives in the user environment only.
- Large inputs/outputs: `backend/data/raw/` (GBs of NASA files), `backend/out/`, `frontend/player/frames/` (gitignored).
- Small derived results in `backend/data/derived/` *are* committed so the app works without downloads.

## Where things are
- Repo overview: `README.md`; backend and how to reproduce every dataset: `backend/README.md`; data notes: `backend/data/README.md`.
- Windows quirks (Smart App Control blocks some DLLs, pandas pinned < 3): see `backend/README.md` → Windows notes.
- Accessibility is a core requirement: keyboard-only, screen-reader live regions, no autoplay (see `docs/04-accessibility.md`).
- Credit NASA sources in captions and `source` fields; never imply NASA endorsement.
