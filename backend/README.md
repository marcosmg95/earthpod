# backend/

Python: data loading, data → music mapping, numpy synth, and the PoC scripts. Commands run from the repo root.

## What's here
| PoC | Script | Needs | Proves |
|---|---|---|---|
| 1 | `scripts/poc1_render_global.py` | `data/gistemp/` (committed) | Real GISTEMP numbers → a musical, explainable track (WAV) |
| 2 | `scripts/poc2_export_tracks.py` | same | `frontend/player/tracks.json` for the accessible web player |
| 3 | `scripts/poc3_validate_inversion.py` | `data/raw/` (run `data/download_data.ps1`) | SVS 5450 frame colours read back into °C match GISTEMP → **r for the Validity slide**; also writes `frontend/player/frames/` |
| 4 | `scripts/poc4_barcelona.py` | gridded netCDF + `pip install netCDF4` | Barcelona-region series → second track ("Listen to Barcelona") |
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
