# data/

## Already here
- `gistemp/GLB.Ts+dSST.csv` — GISTEMP v4 global monthly + annual anomalies (°C vs 1951–1980), 1880–Sep 2026. Downloaded 10 Nov 2026.
- `gistemp/ZonAnn.Ts+dSST.csv` — annual zonal means (Glob, NHem, SHem, 8 latitude bands), 1880–2025.

Missing values are `***`. Values like `-.19` have no leading zero.

## To download (large files)
Run `download_data.ps1` (PowerShell, from this folder). It fills `raw/` with:
- GISTEMP gridded netCDF (2°×2°, monthly; Barcelona region ≈ cell at 41°N, 1–3°E)
- NH / SH tables
- SVS 5450 equirectangular movie (4096×2048, 900 frames; ~6 frames per year), `time.txt` (frame → year), colorbars
- Two full-res PNG frames to validate colormap inversion
- SVS 5313 night-lights EIC movie (2160p, 32:9, H.265, 33 MB) + a print JPG.
  Re-encode for browsers (H.264, 4096 px wide, bundled ffmpeg from `imageio-ffmpeg`): from `backend/`,
  `uv run python -c "from pathlib import Path; from jukebox import video; Path('data/raw/svs5313_EIC_h264.mp4').write_bytes(video.to_h264(Path('data/raw/svs5313_EIC_2160p30_h265.mp4').read_bytes()))"`

## Black Marble night lights (needs an Earthdata token)
`download_blackmarble.ps1` fetches NASA Black Marble VNP46A4 (yearly VIIRS night lights, LAADS collection 5200 v002)
into `raw/blackmarble/`: the data behind SVS 5313. Default: Barcelona tile h18v04, 2012–2023, ~135 MB/tile (~1.6 GB).
Add Kyiv/Delhi with `-Tiles h18v04,h21v03,h25v06`. Set `$env:EARTHDATA_TOKEN` first (steps in the script header).
Then (from `backend/`) `uv run --extra blackmarble python scripts\poc5_blackmarble_regions.py` writes `derived/blackmarble_annual.csv` + `.json`.

The separate `derived/svs5313_eic_frames.csv` contains picture features, not radiance (per frame: overall
bright-pixel level `light` and its centroid `x`, its purple/orange change-map parts, and the same three values inside
each zoom box `weur_*`, `emed_*`, `ukr_*`, `ind_*`; see `jukebox/nightlights_frames.py`): rebuild it from the
SVS 5313 EIC H.265 movie downloaded by `download_data.ps1`, using
`uv run python scripts\poc7_svs5313_features.py` from `backend/`. No Earthdata token is needed. The same script writes
`derived/svs5313_eic_grids.npz`: coarse light grids (world 15x64 per year, purple/orange change maps, and each zoom box
15x20) that the `nightlights_three_acts` sonification scans.

After it runs, frames can be extracted at low res, one per year, e.g.:
`ffmpeg -i raw/svs5450_SOS_4096x2048.mp4 -vf "select=not(mod(n\,6)),scale=360:180" -vsync vfr frames/f%03d.png`
(check `time.txt` for the exact frame→year mapping first).

## Citations
- GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA Goddard Institute for Space Studies. https://data.giss.nasa.gov/gistemp/
- NASA Scientific Visualization Studio, "Global Temperature Anomalies from 1880 to 2024" (SVS 5450). https://svs.gsfc.nasa.gov/5450/
- NASA Scientific Visualization Studio, "Change in Night Lights between 2012 and 2023 - EIC Version" (SVS 5313), visualizer Kel Elkins. https://svs.gsfc.nasa.gov/5313/
- NASA Black Marble VNP46A4 (Román et al.), Suomi NPP VIIRS, NASA LAADS DAAC. https://ladsweb.modaps.eosdis.nasa.gov/
