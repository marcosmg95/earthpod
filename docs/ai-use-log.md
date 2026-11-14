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
| 2026-11-14 | Claude Code | Documented sonification scripts and Windows/uv run rules in AGENTS.md | Marcos | Yes |
| 2026-11-14 | Claude Code | Explored SVS 5196 (DYAMOND CO2); wrote frame-feature extraction from its movies (jukebox/frames.py, poc6 script, derived CSVs) and six sonification scripts, one per technique (parameter mapping, auditory icons, earcons, audification, model-based, full mix); explorer timeline from frame features; tests and docs | Marcos | Pending team review (audio not yet listened to by a human) |
| 2026-11-14 | Copilot | Created the CO2 currents sonification from screen position and spread, with tests and documentation | Marcos | Pending team review (audio not yet listened to by a human) |
| 2026-11-14 | Copilot | Created four body-inspired CO2 sonifications (lungs, blood flow, bubbling fluid, nervous system), with tests and documentation | Marcos | Pending team review (audio not yet listened to by a human) |
| 2026-11-14 | Copilot | Changed the lungs sonification to follow the movie's tan haze rather than its orange-red area, with tests and documentation | Marcos | Pending team review (audio not yet listened to by a human) |
| 2026-11-14 | Copilot | Layered the existing CO2 heartbeat over the haze-driven breathing, with tests and documentation | Marcos | Pending team review (audio not yet listened to by a human) |
| 2026-11-14 | Copilot | Softened the breathing sound and lowered it beneath the heartbeat, with a spectral test | Marcos | Pending team review (audio not yet listened to by a human) |
| 2026-11-14 | Copilot | Reduced the breath level further relative to the heartbeat and checked the mix | Marcos | Pending team review (audio not yet listened to by a human) |
