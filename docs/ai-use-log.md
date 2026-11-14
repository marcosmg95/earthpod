# AI-use log

Space Apps requires disclosing where and how AI tools were used. Log every use from hour 1.

| Date/time | Tool | Used for | Who | Human review? |
|---|---|---|---|---|
| 2026-11-10 | Claude | Early research on challenge, data sources, prior art; drafting these planning docs | Marcos | Yes |
| 2026-11-10 | Claude | Downloaded GISTEMP CSVs (checksums verified), wrote data/download_data.ps1, drafted organizer/ONCE emails, pitch deck skeleton | Marcos | Yes |
| 2026-11-10 | Claude | Wrote poc/ (Python PoCs: GISTEMP→music mapping, numpy synth, colormap inversion + validation, Barcelona extraction, accessible web player, tests) | Marcos | Pending team review |
| 2026-11-14 | Claude Code | Reviewed team concept notes (Earth in layers, same-period rule, event stories); built the "Earth in layers 2012–2023" track (GISTEMP + Black Marble, shared years only), layer on/off/solo controls in the player, tests; added AI-log rule to AGENTS.md | Marcos | Pending team review |
| 2026-11-14 | Claude Code | Refactored backend to a uv project (pyproject.toml + uv.lock, src/jukebox layout, no sys.path hacks); added jukebox.svs API client + Streamlit SVS explorer (apps/svs_explorer.py) and tests; updated READMEs/AGENTS.md | Marcos | Pending team review |
| 2026-11-14 | Claude Code | Diagnosed Smart App Control blocking the streamlit.exe launcher; switched docs to `uv run python -m streamlit` and added a Windows note | Marcos | Yes |
| 2026-11-14 | Claude Code | Added .vscode/launch.json (run/debug entry points); built video-locked data sonification in the SVS explorer (time.txt timeline, sonification script contract + GISTEMP demo, synced HTML player), tests and docs | Marcos | Pending team review |
