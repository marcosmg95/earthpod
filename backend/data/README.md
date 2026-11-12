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

After it runs, frames can be extracted at low res, one per year, e.g.:
`ffmpeg -i raw/svs5450_SOS_4096x2048.mp4 -vf "select=not(mod(n\,6)),scale=360:180" -vsync vfr frames/f%03d.png`
(check `time.txt` for the exact frame→year mapping first).

## Citations
- GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA Goddard Institute for Space Studies. https://data.giss.nasa.gov/gistemp/
- NASA Scientific Visualization Studio, "Global Temperature Anomalies from 1880 to 2024" (SVS 5450). https://svs.gsfc.nasa.gov/5450/
