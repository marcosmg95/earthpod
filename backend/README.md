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
| — | `apps/svs_explorer.py` | internet | Streamlit: type any SVS id → metadata, filterable media list, movie/image previews, datasets, linked pages, raw JSON |
| — | `scripts/fetch_arcade_images.py` | internet | ~34 public-domain NASA images → `frontend/arcade/images` |
| — | `scripts/make_voice.py` | Windows TTS | Arcade voice-over clips → `frontend/arcade/voice` |

## Quick start (Windows, from `backend/`)
```powershell
uv sync                                          # .venv with deps + jukebox (editable) + streamlit
uv run python -m unittest discover -s tests -v
uv run python scripts\poc1_render_global.py      # -> backend\out\earth_jukebox_global.wav
uv run python scripts\poc2_export_tracks.py      # -> frontend\player\tracks.json
uv run streamlit run apps\svs_explorer.py        # SVS explorer, http://localhost:8501/?id=5450
```
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
src/jukebox/svs.py        NASA SVS API client (fetch, flatten media, credits, linked pages)
apps/svs_explorer.py      Streamlit SVS explorer
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
