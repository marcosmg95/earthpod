# AI-use log

Space Apps requires disclosing where and how AI tools were used. Commit-by-commit detail is in the git history.

## Planning and research
- Claude (Anthropic): early research on the challenge, NASA data sources and prior art; drafts of the planning docs and pitch deck skeleton.
- The CCLab team chose the challenge angle, the datasets and the concept (Earth in layers, same-period rule, event stories), and edited the drafts.

## Backend (backend/)
- Claude Code (Anthropic; Claude Opus 5.5, Sonnet 5.5, Fable 5.2) and GitHub Copilot: wrote most of the Python code under the CCLab team's direction —
  data loaders and NASA SVS client, frame and page measurements from the SVS movies, the synth and instrument models,
  the sonification scripts, the Streamlit explorer and live player, the `jukebox.preview` and `jukebox.measure` tools,
  tests, docs, and the CI/CD and Kamal deploy setup.
- The CCLab team directed the work: decided what to sonify and how it should sound (which NASA pages, which techniques, the
  body-inspired CO2 ideas, the switch to electronic instruments for night lights), set the architecture and repo rules
  (uv project, one script per SVS page, `AGENTS.md`), reviewed and ran every change, and kept the tests green before
  each commit.
- AI also checked its own work numerically (bit-identical audio before/after refactors, pitch/level/pan tests,
  contact sheets of the movies), but the final listening and sign-off on the audio is done by the team.

## Frontend (frontend/web)
- Claude (Anthropic): help with stack choice, code, UI design and accessibility review. All code reviewed and tested by the team.
- Kokoro-82M (Apache-2.0): text-to-speech voice for the intro narration.
