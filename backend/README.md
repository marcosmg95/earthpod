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
| 7 | `scripts/poc7_svs5313_features.py` | SVS 5313 EIC movie from `data/download_data.ps1` | Screen-space light features for the night-lights nervous-system sonification |
| 8 | `scripts/poc8_page_features.py [ids]` | internet (downloads ~2.6 GB of movies into `data/raw/`, resumable) | Frame measurements of the other Resources-tab pages (5669, 5533, 5011, 3912, 5425, 4960, 4950) → `data/derived/svs<id>_*` |
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
The explorer's **Sonify** tab: pick a movie and a script; it renders automatically (and again about a second after any
slider change; the last 6 renders are cached; a toggle switches back to a Render button for slow scripts). The video's
play/pause/seek/speed drive the audio (the `<video>` is the master clock; the audio re-syncs if it drifts by more than
80 ms). The player (`apps/live_player.py` + `apps/live_player/index.html`, a Streamlit component) stays mounted: new
audio swaps in at the current time without stopping the video.
After rendering, download the sonification as a WAV and optionally prepare a video-only download of the original
SVS movie; the sonification is not embedded in that video.
Scripts are grouped by SVS page: `sonifications/svs<id>/` (e.g. `svs5196/` = CO2, `svs5313/` = night lights,
`svs5669/` = aerosols, `svs5450/` = GISTEMP demo, not on the Resources tab) and the tab only offers the folder of the page you are on, plus any generic script placed
directly in `sonifications/` (shown for every page). New page → new `svs<id>/` folder.
Script names are sorted numerically within their text, so `co2_2` appears before `co2_10`.
The timeline (which data label is on screen at each moment) comes from the page's `time.txt` (one label per frame,
e.g. SVS 5450) and the frame rate in the frame-folder name (`…_30p`); without a time.txt you give a year range and length.
A script is a plain `.py` file; copy `sonifications/svs5450/gistemp_lead.py` to start:
```python
TITLE = "Short name"
DESCRIPTION = "What data, what mapping."
def render(ctx):                  # ctx: jukebox.sonify.SonifyContext
    notes = ctx.notes_from_series(my_series_by_year, mapping.DEFAULT_VOICES[0])  # one note per on-screen year
    return ctx.render_notes(notes)  # or any stereo numpy array (n, 2) at ctx.sr; sample 0 = video time 0
```
`ctx.timeline.spans()` gives `(label, t0, t1)` for custom mappings. Scripts are re-imported on every Render, so edit and re-render without restarting.

**Fast iteration (terminal).** The explorer needs a browser round-trip; `jukebox.preview` renders and plays from the terminal instead:
```powershell
cd backend
uv run python -m jukebox.preview co2_15 --start 20 --end 35 --watch      # save the .py -> it re-renders and plays
uv run python -m jukebox.preview co2_15 --set BREATH_GAIN=0.5            # try a value without editing the file
```
`co2_15` is any unique name/prefix (or a path). It renders the whole movie (~1 s for the CO2 scripts), then plays only
`--start`..`--end` seconds, so loudness is identical to the explorer; the WAV is `backend/out/preview/<script>.wav`.
`--watch` re-runs when any `.py` in the script's folder is saved (errors are printed and it keeps watching;
changes under `src/jukebox/` need a restart). Defaults: SVS 5196 orbit movie, 30 fps; `--movie zoom`, `--fps`, `--viz` change that.

**Tunable constants.** List module constants in `PARAMS = {"BREATH_GAIN": (0.0, 1.0)}` (name → (min, max); the constant's value is
the default). They become sliders in the Sonify tab (with a copy-paste block of the changed values) and `--set NAME=VALUE`
in the terminal. `render()` must read the constant when it runs, not at import time.

**Stems: live levels without re-rendering.** `render()` may return named layers instead of one array, with
`STEMS = {"breath": "BREATH_GAIN", ...}` naming the constant that sets each layer's level (plus an optional `OUTPUT_GAIN`).
The mix is `normalize(sum(level * stem)) * OUTPUT_GAIN` (`sonify.Stems.mix`, also what `sonify.run`, `jukebox.preview` and the
WAV download produce); the explorer's player redoes it in the browser, so those sliders sit under the video and act at once.
`render()` must not use the level constants itself. Example: `svs5196/co2_15_lungs_heart_region.py`.

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

**SVS 5313 (Black Marble night lights):** select the `nightlights_flat_series_and_change_wZooms_13_EIC_2160p30_h265.mp4`
movie. The committed per-frame features give a 1,300-frame timeline at 30 fps. Its labels (year or change map,
global or zooms) and the player's three section buttons come from `jukebox/nightlights_frames.py`, where the
scene boundaries and the frames at which each year label appears were read from the movie by hand:

| Section | Frames | Seconds | On screen |
|---|---|---|---|
| 1 · Years 2012–2023 | 0–288 | 0–9.6 | global map, one year every ~0.6 s from frame 15 |
| 2 · Change map | 289–630 | 9.6–21 | purple = "new lights", orange = "lights out" (SVS legend) |
| 3 · Regional zooms | 631–1299 | 21–43.3 | boxes fade in (frames 668–690) over the years again (from frame 830), then as a change map from frame 1104 |

- `nightlights_three_acts`: every act scans the map left to right (pan = longitude, pitch = latitude with north
  high, loudness = brightness, pentatonic notes). Act 1 sweeps the world once per year with plucks and adds a bell
  wherever a place is brighter than in 2012; Act 2 sweeps the change map three times (purple as high bells, orange
  as low plucks, then both at their true balance); Act 3 tours the four zoom boxes (left to right Western Europe,
  Eastern Mediterranean, Ukraine, India), sweeps all four every year, and tours the final change map. Each section
  is set to the same loudness, so the sparse orange pass is boosted; the sweeps come from coarse grids measured
  from the movie's pictures (`nightlights_frames.extract_grids`), not from the per-frame CSV.
- `nightlights_grid_and_regions` (stem script, the night-lights cousin of `co2_15`): background = a 49 Hz (G1, ~50 Hz
  mains) electrical hum, louder in the brighter years of each scene and brighter in tone while the lights grow, plus a
  clock tick at every year-label change (1 year = 1 beat). Foreground = one electronic instrument per region: three
  longitude bands of the world map in sections 1–2 (Americas synth pluck, Europe + Africa pulse-wave lead, Asia
  chiptune square), then the four zoom boxes from frame 668 (Western Europe FM electric piano, Eastern Mediterranean
  FM glass bell, Ukraine theremin-like sine lead, India saw bass). Register =
  latitude, pan = longitude / box position, shared D minor pentatonic; pitch in the year scenes = that year's
  brightness ranked among the region's years. In the change maps each region in turn plays a rising run (loudness =
  purple "new lights") and a falling run (orange "lights out"), then all hold a final note, high where new lights
  win and low where lights went out. The synths are `jukebox.instruments.ELECTRONIC` (band-limited saw / square /
  pulse with a filter envelope, and 2-operator FM); `co2_15`'s acoustic models live in the same module.
- `nightlights_nervous_system`: an electrical murmur whose loudness follows bright-pixel intensity, stereo
  position the bright areas' screen position, and shimmer changes in intensity; it does not tell increases from
  decreases. The map shows Earth twice side by side, so screen position is only loosely geographic.

The central year label and legend are masked, but other overlays, map details, transitions and zooms still
influence the sound. These are picture indices, not calibrated radiance or individual cities. Purple/orange are
classified by hue (gold year-map lights fall outside both ranges). The H.265 movie requires browser support
for that codec. Other movie versions have not been measured.

To reproduce the features, download the SVS 5313 movie with `data\download_data.ps1`, then run
`uv run python scripts\poc7_svs5313_features.py` from `backend/`. This writes
`data\derived\svs5313_eic_frames.csv` and `data\derived\svs5313_eic_grids.npz` (world and zoom-box light grids);
no Earthdata token is needed (the run decodes the 8K movie, so it takes a few minutes).

**The other pages on the challenge's Resources tab** (besides 5196 and 5313) are measured by one module each in
`src/jukebox/pages/svs<id>.py` (same contract: `MOVIE`, `URL`, `FPS`, `extract(path)`, `labels(table)`, optional
`CHAPTERS`; the docstring lists every column). `scripts\poc8_page_features.py` downloads the movie, measures it and
writes `data\derived\svs<id>_frames.csv` + `svs<id>_arrays.npz` (committed, < 1 MB each). Scripts read them with
`ctx.page_features()`: `.table` (one row per frame), `.arrays` (grids / profiles, frames first),
`.column(name, n, sr, smooth)` (a column stretched to audio samples). The explorer and `jukebox.preview` take the
timeline (labels, fps) and the chapter buttons from these files. All values are **picture indices** (colour share,
darkness, motion on screen), not physical units; each module's docstring says what they are and are not.

| SVS | Movie measured | Timeline labels | Script (stems) | What you hear |
|---|---|---|---|---|
| 5669 GEOS Aerosols | the 1920x1080 **still** map (19 Aug 2025) | longitude of the scan line | `aerosols_scan` (6) | a 48 s west→east scan: wind = all aerosol, a tick every 30°, sulfate vibraphone, dust marimba, smoke (black carbon) cello, sea salt flute; pitch = latitude, loudness = amount |
| 5533 Air Quality | `EIC_AirQuality_Preview_3840x1080.mp4` (75 s) | pollutant panel at the screen centre | `pollutant_quartet` (6) | CO cello, PM2.5 marimba, NOx oboe, O3 flute panned to their panels; pitch = latitude of the darkest areas, loudness = concentration index, bell on the darkest plumes; a drone that beats faster the dirtier the strip; a call sign per new centre panel |
| 5011 ISS lightning | `iss_lightning_sos_yearly_07312023_2048p60.mp4` (100 s, map) | season shown (north / south / both) | `storm_map` (6) | a chord that rises with northern-hemisphere storms, thunder = new flashes, an electric click per 10° cell that lights up (pan = longitude, pitch = latitude), Americas / Africa-Europe / Asia-Oceania instruments |
| 3912 ECCO2 currents + SST | `ecco2_sst_flow.mp4` (67 s, flat map) | frame number (no dates on the page) | `warm_and_cold_currents` (5) | sea noise (motion, warmth), Pacific cello / Atlantic flute / Indian vibraphone (pitch = warmth, loudness = motion), a west→east radar sweep every 8 s with bells for warm water and plucks for cold |
| 5425 Perpetual Ocean 2 | `perpetual_ocean2_CLOSE_093_clean_noDate_1080p30.mp4` (317 s) | model date 15 Jan 2021 – 25 Dec 2023 | `boundary_currents` (3) | rolling sea (closer camera = louder), a tick per model month, a cello following the white fast-current streamlines and a harp for their height and swirl |
| 4960 Atmospheric river | `atmos_river_HD.mp4` (292 s) | model date + hour, read from `atmos_river_DATE_ONLY_HD.mp4` with glyph templates | `river_rain_clock` (3) | rushing air + flute for the moisture band, rain drops, a tick every 6 model hours (the movie's time jumps and replays: a swoop marks each jump back) |
| 4950 GEDI forest height | `GEDI_global_w_colorbar_1080p60.mp4` (51 s, one turn of the globe) | longitude facing the camera | `forest_meridian` (5) | ocean hush, leaf rustle, a harp arpeggio down the meridian facing you (pitch = latitude, louder = taller-looking forest), a cello for the tallest forest, ticks every 30° |

Notes. **5669 is a still image**: the explorer shows it with a moving scan line, a Play button and a position slider
(the player's `Clock` stands in for the `<video>`; keyboard: Tab to Play, Space/Enter, arrow keys on the slider).
**Movies longer than 120 s** (5425, 4960) are rendered at 16 kHz (`sonify.sample_rate_for`) so each stem stays ~20 MB
in the page; their scripts keep to three stems. **5011** prints no dates and its storms swing between hemispheres
7.7 times (more than the 6.6 years the page states), so it is labelled by season, not date. **5533** panels are
assigned by colour, and CO / PM2.5 (same hue) by the fixed panel order. **4950** brightness is also shaped by the
virtual sun and the exaggerated height, so its forest levels are relative to the movie.

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
apps/live_player.py       video-master / audio-follower player, live stem mixer (Streamlit component: live_player/index.html)
apps/sync_player.py       older single-WAV player (HTML+JS in st.iframe); no longer used by the explorer
src/jukebox/frames.py     per-frame colour features of a movie (SVS 5196 CO2), used by co2_*.py
src/jukebox/nightlights_frames.py  per-frame screen-light features of the SVS 5313 EIC movie
src/jukebox/pages/        one module per other Resources-tab page (svs5669.py ...): measures its movie / still image
sonifications/svs<id>/    sonification scripts per SVS page (svs5450/gistemp_lead.py = demo, svs5196/co2_*.py, svs5313/)
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
