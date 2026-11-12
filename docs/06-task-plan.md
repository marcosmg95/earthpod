# 06 — Task plan

Owner roles (assign at kickoff): **DATA** (Python prep, validation) · **AUDIO** (Tone.js engine, mapping) · **UX/A11Y** (UI, keyboard, ARIA, testing) · **STORY** (pitch, video, README, submission). Marcos likely DATA or AUDIO.

## Before the event — research & prep only (no product code until rules confirm it's allowed)

### Tue 10 Nov
- [x] Early investigation (docs/01–05)
- [ ] Share these docs with the team; agree on concept A+B
- [ ] Assign roles (+ who owns how it sounds)
- [ ] Verify all members registered for the Barcelona event and CCLab joined the challenge

### Wed 11 Nov
- [x] DATA: GISTEMP global + zonal CSVs saved in data/gistemp/
- [ ] DATA: run data/download_data.ps1 (netCDF, SVS 5450 movie, time.txt, colorbars); check Barcelona cell series
- [ ] DATA: inspect SVS 5450 / 5603 pages — frame resolutions, `time.txt`, colorbar
- [ ] UX/A11Y: email 42 Barcelona organizers / ONCE asking for a blind or low-vision tester (~20 min, Sun morning)
- [ ] Ask organizers: pitch language/length, overnight stay, exact deadline + time zone, room audio
- [ ] DATA: check Observatori Fabra / Meteocat long series for a real Barcelona station track
- [ ] AUDIO: try a 20-line Tone.js prototype outside the repo to learn the API (throwaway)

### Thu 12 Nov
- [ ] All: review mapping table (docs/03) and keyboard model (docs/04)
- [ ] DATA: download low-res frame range for SVS 5450 (test curl range)
- [ ] STORY: draft one-sentence mapping + pitch skeleton
- [ ] Set up empty GitHub repo + GitHub Pages/Vercel (no product code), README stub, LICENSE
- [ ] Install NVDA (Windows) for screen-reader testing
- [ ] Shortlist instrument samples with compatible licences (CC0 preferred; credit CC-BY)
- [ ] Prepare tester consent form (quote + recording)

### Fri 13 Nov — guides released
- [ ] Read challenge Resources tab; adjust datasets if NASA names specific ones
- [ ] Read Project Submission Guide + Judging guide: video length, required fields, AI disclosure wording, "code written during event" rule
- [ ] Update docs/07 checklist accordingly
- [ ] Pack: laptops, several headphones, chargers, extension cord, portable speaker, ID
- [ ] Agree sleep shifts so someone is fresh for Sunday video + submission

## Hackathon — Sat 14 Nov (hours from start)

### H0–6
- [ ] Kickoff: confirm roles, freeze mapping table
- [ ] DATA: `prep.py` → `tracks.json` (global, 4 zonal bands, Barcelona) + downsampled frames
- [ ] AUDIO: engine plays global track: tonic drone + pentatonic melody, Transport synced to years
- [ ] UX/A11Y: page skeleton — Play/Pause, volume, year slider (native controls, aria-valuetext)

### H6–14
- [ ] AUDIO: zonal voices with pan (Arctic highest), dissonance on extremes, record-year accents
- [ ] UX/A11Y: keyboard model, aria-live narration (throttled), frame sync display
- [ ] DATA: Barcelona track (5-yr smoothing) + planet↔Barcelona toggle data
- [ ] AUDIO: duck music while screen reader / narration speaks
- [ ] All: listening session — does it sound good? (repeat every few hours)
- [ ] STORY: AI-use log up to date; start README (data citations, mapping)

### H14–20
- [ ] DATA: colorbar inversion + validation plot (inverted frame mean vs GISTEMP)
- [ ] UX/A11Y: orientation intro track, reference tone, transcripts, alt text (CA/ES/EN)
- [ ] AUDIO: optional haptics (feature-detected, Android)
- [ ] Deploy first public version

## Hackathon — Sun 15 Nov

### H20–30
- [ ] UX/A11Y: session with blind/low-vision tester; record feedback + quote (with permission)
- [ ] All: fix top issues from the test
- [ ] Stretch (only if stable): hover-to-hear on SVS 5176 SST anomaly

### H30–40
- [ ] STORY: demo video (captions + audio description), slides (problem → mapping → validity → quote → Barcelona → demo)
- [ ] STORY: README final — data citations, GIBS acknowledgement, no NASA logo, AI-use statement
- [ ] All: final accessibility pass (docs/04 must-haves); test iPhone with silent switch off
- [ ] STORY: offline backup of demo video for the pitch
- [ ] Submit ≥2 h before deadline; verify project page, repo and live URL load

## After
- [ ] Present locally; collect judge feedback
- [ ] Watch for Global nominees (Dec 2026)
