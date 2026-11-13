# backend/

Python: data loading, data → music mapping, numpy synth, and the PoC scripts. Commands run from the repo root.

## What's here
| PoC | Script | Needs | Proves |
|---|---|---|---|
| 1 | `scripts/poc1_render_global.py` | `data/gistemp/` (committed) | Real GISTEMP numbers → a musical, explainable track (WAV) |
| 2 | `scripts/poc2_export_tracks.py` | same | `frontend/player/tracks.json` for the accessible web player |
| 3 | `scripts/poc3_validate_inversion.py` | `data/raw/` (run `data/download_data.ps1`) | SVS 5450 frame colours read back into °C match GISTEMP → **r for the Validity slide**; also writes `frontend/player/frames/` |
| 4 | `scripts/poc4_barcelona.py` | gridded netCDF + `pip install netCDF4` | Barcelona-region series → second track ("Listen to Barcelona") |
| 5 | `scripts/poc5_blackmarble_regions.py` | `data/download_blackmarble.ps1` (Earthdata token) + `pip install h5py` | Black Marble night lights (SVS 5313 data) per region/year → `data/derived/blackmarble_annual.*` |
| — | `scripts/fetch_arcade_images.py` | internet | ~34 public-domain NASA images → `frontend/arcade/images` |
| — | `scripts/make_voice.py` | Windows TTS | Arcade voice-over clips → `frontend/arcade/voice` |

## Quick start (Windows, from the repo root)
```powershell
pip install -r backend\requirements.txt
python -m unittest discover -s backend\tests -v
python backend\scripts\poc1_render_global.py           # -> backend\out\earth_jukebox_global.wav
python backend\scripts\poc2_export_tracks.py           # -> frontend\player\tracks.json
```
After `backend\data\download_data.ps1` (~180 MB into `backend\data\raw`, gitignored):
```powershell
python backend\scripts\poc3_validate_inversion.py      # r + backend\data\derived\validation_svs5450.* + frontend\player\frames
python backend\scripts\poc4_barcelona.py               # backend\data\derived\barcelona_annual.csv
python backend\scripts\poc2_export_tracks.py           # re-export: adds Barcelona track + frames
```

### Reproduce the night-lights track (PoC 5, NASA Black Marble / SVS 5313)
The outputs (`backend\data\derived\blackmarble_annual.*`, the `night` track in `frontend\player\tracks.json`) are
committed, so this is only needed to rebuild them or add cities.
1. Free Earthdata account (https://urs.earthdata.nasa.gov/users/new), then on https://ladsweb.modaps.eosdis.nasa.gov/
   log in → profile → **Generate Token**. Store it once per PC (never commit it, never paste it in chat):
   `[Environment]::SetEnvironmentVariable("EARTHDATA_TOKEN", "<token>", "User")`, then open a new terminal.
2. Download (~1.45 GB Barcelona + ~1.8 GB Kyiv into `backend\data\raw\blackmarble`, gitignored; reruns skip finished files):
   ```powershell
   powershell -ExecutionPolicy Bypass -File backend\data\download_blackmarble.ps1 -Tiles h18v04,h21v03
   ```
3. Build:
   ```powershell
   python backend\scripts\poc5_blackmarble_regions.py     # -> backend\data\derived\blackmarble_annual.csv/.json
   python backend\scripts\poc2_export_tracks.py           # -> tracks.json gains the "night" track
   ```
   `poc2` also needs `backend\data\raw\svs5450_time.txt` (from `download_data.ps1`, or just
   `curl -o backend\data\raw\svs5450_time.txt https://svs.gsfc.nasa.gov/vis/a000000/a005400/a005450/time.txt`);
   without it the temperature tracks lose their frame numbers.

Expected: Barcelona ≈ −10% vs 2012 (31.7 → 28.7 nW/cm²/sr); Kyiv 2022 −59% in one year (15.1 → 6.2).
Add Delhi with tile `h25v06` (the region box already exists in `jukebox/blackmarble.py`).

### Windows notes
- Smart App Control blocks pandas 3.x and netCDF4 DLLs (“Una directiva de Control de aplicaciones bloqueó este archivo”).
  `requirements.txt` pins pandas < 3; netCDF4 is only needed to re-run PoC 4.
- LAADS occasionally returns a transient 404; the download script retries 3 times.

## The mapping (one sentence for the pitch)
One year = one note; each 0.1 °C of global warming raises the melody one step of a D minor pentatonic
scale; the low drone is 0 °C (1951–1980 average). Strings = latitude bands, Arctic highest. Tempo speeds up
with the rate of warming, a tritone clashes above +1 °C, a bell marks each new record year.
All parameters live in `jukebox/mapping.py` (`DEFAULT_VOICES`, `SCALE`, `TONIC_MIDI`) — tune them in listening sessions.

## Layout
```
jukebox/data.py      GISTEMP loaders, frame<->year (time.txt); reads backend/data/
jukebox/mapping.py   data -> notes (scale quantization, tempo, dissonance, records, descriptions)
jukebox/synth.py     numpy synth -> stereo WAV (no audio libraries)
jukebox/colormap.py  colorbar LUT (CIELAB), frame inversion, cos(lat) area mean
scripts/             PoC entry points (see table above)
tests/test_poc.py    data, mapping, synth, synthetic colormap round trip
data/                gistemp/ (committed), derived/, raw/ (downloaded, gitignored) — see data/README.md
out/                 rendered audio (gitignored)
```

## Known limits / next steps
- PoC 3 assumes the SOS movie is equirectangular with no overlays; check coverage % it prints. If r < 0 use `--flip`.
- Movie frames are compressed (H.264); `--max-de` trades coverage vs. accuracy.
- Player (`frontend/player`): scheduling is basic; for the MVP move to Tone.js (Transport, Sampler) and add transcripts + CA/ES translations.
- Barcelona: a 2° cell is ~200 km — call it "the Barcelona region"; consider Observatori Fabra / Meteocat station data.

Data: GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA GISS.
Frames: NASA Scientific Visualization Studio, SVS 5450. Not endorsed by NASA.
