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

- Claude (Anthropic; claude.ai, Claude Opus 5.5): helped choose the stack (Vite, React, TypeScript, wouter, zod) and
  wrote most of the frontend code under the team's direction: the ESLint/Prettier setup (jsx-a11y strict, custom rules
  against autoplay and unthrottled live regions), the intro film, chapter flow, player, sound chart, audio/video sync,
  dot-matrix globe (d3-geo, Natural Earth), 00 How to listen, header menu, the accessibility statement draft,
  the Playwright + axe end-to-end tests, the waveform script, the app icon, and the Dockerfile/nginx/CI changes.
  It also made the UI mockups on design canvases and reviewed the repo, the live site (axe scans, 400% zoom and
  text-spacing checks) and the texts against the NASA SVS 5196 and 5313 pages.
  For the SVS 5669 aerosols scene, Claude Code also drafted the scene descriptions (`.vtt`) from the measured
  data and the NASA page, and exported the scan-line video and audio with `backend/scripts/export_still_scene.py`, and the "How to listen"
  samples for the aerosols and night-lights scenes with `backend/scripts/export_samples.py`.
  It later shortened the cue text of all three scene `.vtt` files (about 3 words per second, same timings) so that
  captions can be read and screen readers can keep up.
- Kokoro-82M (open-weight text-to-speech, Apache-2.0): the synthetic voice of the intro narration, generated with
  `scripts/make_narration_kokoro.py` (lower pitch and room reverb with ffmpeg). The words are the team's own.
- The CCLab team directed the work: chose the concept, the cinematic flow, the palette, font and layouts (picking
  between mockups), the narration text and voice, and what to simplify; reviewed and ran every change, fixed
  formatting and build errors, and tested in the browser before each deploy.
- Accessibility was checked automatically (axe, end-to-end tests) and by the team with the keyboard; the final
  sign-off on screen-reader use is done by the team.

## Release documentation

- GitHub Copilot: assisted with consolidating the project README and release-facing documentation. Product claims were checked against the application and repository documentation; maintainers should review the final wording before external submission.
