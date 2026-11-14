# backend/

Python: data loading, data → music mapping, numpy synth, the PoC scripts and a Streamlit SVS explorer.
Managed with [uv](https://docs.astral.sh/uv/) — install once with `pip install uv` (or `winget install astral-sh.uv`).
**Commands run from `backend/`.**

## What's here
| PoC | Script | Needs | Proves |
|---|---|---|---|
| 1 | `scripts/poc1_render_global.py` | `data/gistemp/` (committed) | Real GISTEMP numbers → a musical, explainable track (WAV) |
| 2 | `scripts/poc2_export_tracks.py` | same | `frontend/player/tracks.json` for the accessible web player |
| 3 | `scripts/poc3_validate_inversion.py` | `data/raw/` (run `data/download_data.ps1`) | SVS 5450 frame colours read back into °C match GISTEMP → **r for the Validity slide**; also writes `frontend/player/frames/` |
| 4 | `scripts/poc4_barcelona.py` | gridded netCDF + `--extra netcdf` | Barcelona-region series → second track ("Listen to Barcelona") |
| 5 | `scripts/poc5_blackmarble_regions.py` | `data/download_blackmarble.ps1` (Earthdata token) + `--extra blackmarble` | Black Marble night lights (SVS 5313 data) per region/year → `data/derived/blackmarble_annual.*` |
| — | `apps/svs_explorer.py` | internet | Streamlit: type any SVS id → metadata, filterable media list, movie/image previews, datasets, linked pages, raw JSON; **Sonify** tab plays a data sonification locked to a movie |
| — | `scripts/fetch_arcade_images.py` | internet | ~34 public-domain NASA images → `frontend/arcade/images` |
| — | `scripts/make_voice.py` | Windows TTS | Arcade voice-over clips → `frontend/arcade/voice` |

## Quick start (Windows, from `backend/`)
```powershell
uv sync                                          # .venv with deps + jukebox (editable) + streamlit
uv run python -m unittest discover -s tests -v
uv run python scripts\poc1_render_global.py      # -> backend\out\earth_jukebox_global.wav
uv run python scripts\poc2_export_tracks.py      # -> frontend\player\tracks.json
uv run python -m streamlit run apps\svs_explorer.py        # SVS explorer, http://localhost:8501/?id=5450
```
In VS Code, the same entry points are in **Run and Debug** (Ctrl+Shift+D, `.vscode/launch.json`): SVS explorer,
tests, PoC 1/2, arcade and player web servers, current file. Breakpoints work in the Streamlit app and in sonification scripts.

### Sonification scripts (`sonifications/`)
The explorer's **Sonify** tab: pick a movie and a script → **Render** → the video's play/pause/seek/speed drive the audio
(the `<video>` is the master clock; the audio re-syncs if it drifts by more than 80 ms).
The timeline (which data label is on screen at each moment) comes from the page's `time.txt` (one label per frame,
e.g. SVS 5450) and the frame rate in the frame-folder name (`…_30p`); without a time.txt you give a year range and length.
A script is a plain `.py` file; copy `sonifications/gistemp_lead.py` to start:
```python
TITLE = "Short name"
DESCRIPTION = "What data, what mapping."
def render(ctx):                  # ctx: jukebox.sonify.SonifyContext
    notes = ctx.notes_from_series(my_series_by_year, mapping.DEFAULT_VOICES[0])  # one note per on-screen year
    return ctx.render_notes(notes)  # or any stereo numpy array (n, 2) at ctx.sr; sample 0 = video time 0
```
`ctx.timeline.spans()` gives `(label, t0, t1)` for custom mappings. Scripts are re-imported on every Render, so edit and re-render without restarting.

**SVS 5196 (DYAMOND global CO2)** has no time.txt and no downloadable numbers, so its scripts use the movie itself:
`scripts\poc6_svs5196_features.py` measures every frame (how much of the picture is orange-red = dense CO2, where it is,
tan haze, a 120-column left-to-right profile) into `data\derived\svs5196_*` (committed; `jukebox/frames.py`). It is an
index of the picture, not ppm. The orbit movie prints its date (1 frame = 1 model hour, 14 Jan – 3 Mar 2020), which
becomes the timeline. Scripts read it with `ctx.frame_features()`; one script per sonification technique:

| Script | Technique | What you hear |
|---|---|---|
| `co2_1_pulse_melody` | Parameter mapping | pitch = orange-red area, left/right = where on screen, string = daily haze |
| `co2_2_breath_and_fire` | Auditory icons | in/out breath on the daily pulse, fire crackles, haze wind |
| `co2_3_calendar_earcons` | Earcons | day tick, week, month, daily peak, record bell |
| `co2_4_audification` | Audification | each frame's screen profile played directly as the wave (110 cycles/s) |
| `co2_5_struck_bars` | Model-based | 8 bars = 8 screen strips, tapped once a day; CO2 sets loudness, brightness, ring time |
| `co2_6_full_mix` | 1 + 3 + 2 layered | melody + markers + quiet breath |
| `co2_7_heartbeat` | Parameter mapping | one heartbeat per daily pulse: lub = red appears, dub = red fades; louder = bigger pulse |
| `co2_8_currents` | Parameter mapping | screen height = pitch, horizontal position = pan, horizontal spread = chord width; image indices, not altitude or wind |
| `co2_9_lungs` | Auditory icon + heartbeat | centered breath and quiet flow follow tan haze; the heartbeat follows the orange-red pulse |
| `co2_10_blood_flow` | Auditory icon | continuous internal rush follows orange-red area and screen position, without a heartbeat |
| `co2_11_living_fluid` | Auditory icon | bubbles become more frequent with more orange-red area and follow its screen position |
| `co2_12_nervous_system` | Auditory icon | electrical murmur follows orange-red area; faster change makes it shimmer faster |

These four living-body sounds are metaphors derived from the image, not measurements of bodily processes.

Building blocks for new scripts: `synth.band_noise`, `synth.pan_stereo`, `synth.add_at`, `synth.normalize`.
After `data\download_data.ps1` (~180 MB into `backend\data\raw`, gitignored):
```powershell
uv run python scripts\poc3_validate_inversion.py                # r + data\derived\validation_svs5450.* + frontend\player\frames
uv run --extra netcdf python scripts\poc4_barcelona.py          # data\derived\barcelona_annual.csv
uv run python scripts\poc2_export_tracks.py                     # re-export: adds Barcelona track + frames
```

### Reproduce the night-lights track (PoC 5, NASA Black Marble / SVS 5313)
The outputs (`backend\data\derived\blackmarble_annual.*`, the `night` track in `frontend\player\tracks.json`) are
committed, so this is only needed to rebuild them or add cities.
1. Free Earthdata account (https://urs.earthdata.nasa.gov/users/new), then on https://ladsweb.modaps.eosdis.nasa.gov/
   log in → profile → **Generate Token**. Store it once per PC (never commit it, never paste it in chat):
   `[Environment]::SetEnvironmentVariable("EARTHDATA_TOKEN", "<token>", "User")`, then open a new terminal.
2. Download (~1.45 GB Barcelona + ~1.8 GB Kyiv into `backend\data\raw\blackmarble`, gitignored; reruns skip finished files):
   ```powershell
   powershell -ExecutionPolicy Bypass -File data\download_blackmarble.ps1 -Tiles h18v04,h21v03
   ```
3. Build:
   ```powershell
   uv run --extra blackmarble python scripts\poc5_blackmarble_regions.py   # -> data\derived\blackmarble_annual.csv/.json
   uv run python scripts\poc2_export_tracks.py                             # -> tracks.json gains the "night" track
   ```
   `poc2` also needs `backend\data\raw\svs5450_time.txt` (from `download_data.ps1`, or just
   `curl -o backend\data\raw\svs5450_time.txt https://svs.gsfc.nasa.gov/vis/a000000/a005400/a005450/time.txt`);
   without it the temperature tracks lose their frame numbers.

Expected: Barcelona ≈ −10% vs 2012 (31.7 → 28.7 nW/cm²/sr); Kyiv 2022 −59% in one year (15.1 → 6.2).
Add Delhi with tile `h25v06` (the region box already exists in `src/jukebox/blackmarble.py`).

### Windows notes
- Smart App Control blocks pandas 3.x and netCDF4 DLLs (“Una directiva de Control de aplicaciones bloqueó este archivo”).
  `pyproject.toml` pins pandas < 3; netCDF4 is only needed to re-run PoC 4.
- LAADS occasionally returns a transient 404; the download script retries 3 times.
- Smart App Control also blocks the unsigned `.exe` launchers uv puts in `.venv\Scripts` (e.g. `streamlit.exe`,
  "os error 4551"). Run tools through Python instead: `uv run python -m streamlit ...`, `uv run python -m pip ...`.

## The mapping (one sentence for the pitch)
One year = one note; each 0.1 °C of global warming raises the melody one step of a D minor pentatonic
scale; the low drone is 0 °C (1951–1980 average). Strings = latitude bands, Arctic highest. Tempo speeds up
with the rate of warming, a tritone clashes above +1 °C, a bell marks each new record year.
All parameters live in `src/jukebox/mapping.py` (`DEFAULT_VOICES`, `SCALE`, `TONIC_MIDI`) — tune them in listening sessions.

## Layout
```
pyproject.toml            uv project: deps, extras (netcdf, blackmarble), group explorer (streamlit); uv.lock committed
src/jukebox/data.py       GISTEMP loaders, frame<->year (time.txt); reads backend/data/
src/jukebox/mapping.py    data -> notes (scale quantization, tempo, dissonance, records, descriptions)
src/jukebox/synth.py      numpy synth -> stereo WAV (no audio libraries)
src/jukebox/colormap.py   colorbar LUT (CIELAB), frame inversion, cos(lat) area mean
src/jukebox/blackmarble.py  Black Marble HDF5 tiles -> regional radiance
src/jukebox/svs.py        NASA SVS API client (fetch, flatten media, credits, linked pages, time.txt, fps)
src/jukebox/sonify.py     Timeline (frame -> label), SonifyContext, script loader/runner
apps/svs_explorer.py      Streamlit SVS explorer
apps/sync_player.py       video-master / audio-follower player (HTML+JS in st.iframe)
src/jukebox/frames.py     per-frame colour features of a movie (SVS 5196 CO2), used by co2_*.py
sonifications/            sonification scripts shown in the Sonify tab (gistemp_lead.py = demo, co2_*.py = SVS 5196)
scripts/                  PoC entry points (see table above)
tests/                    unittest: data, mapping, synth, colormap round trip, layers, Black Marble, SVS parsing
data/                     gistemp/ (committed), derived/, raw/ (downloaded, gitignored) — see data/README.md
out/                      rendered audio (gitignored)
```

## Known limits / next steps
- PoC 3 assumes the SOS movie is equirectangular with no overlays; check coverage % it prints. If r < 0 use `--flip`.
- Movie frames are compressed (H.264); `--max-de` trades coverage vs. accuracy.
- Player (`frontend/player`): scheduling is basic; for the MVP move to Tone.js (Transport, Sampler) and add transcripts + CA/ES translations.
- Barcelona: a 2° cell is ~200 km — call it "the Barcelona region"; consider Observatori Fabra / Meteocat station data.

Data: GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA GISS.
Frames: NASA Scientific Visualization Studio, SVS 5450. Not endorsed by NASA.
