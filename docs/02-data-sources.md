# 02 — Data sources

## NASA SVS (where EIC visuals live)
- EIC gallery: https://svs.gsfc.nasa.gov/gallery/earth-information-center/
- Earth Now dashboard: https://svs.gsfc.nasa.gov/gallery/earth-now-dashboard/
- Daily visualizations: https://svs.gsfc.nasa.gov/gallery/whats-newwith-earth-today/
- Formats: MP4/WebM + frame directories (TIF/EXR, often PNG/JPG). Frame ranges downloadable with curl, e.g.
  `curl -LO "https://svs.gsfc.nasa.gov/vis/.../frames/1024x512/name.[0060-0119].png"`

| SVS ID | Visualization | Notes |
|---|---|---|
| 5450 / 5207 / 5603 | Global Temperature Anomalies 1880–2024/23/25 | 5450: 900 frames 3840x2160; 5207 has `time.txt`; 5603 has `GISTEMPtime.txt`, colormap "vik" |
| 4626 / 4882 / 4964 | Older temperature anomaly versions | Separate colorbar PNGs (unverified) |
| 5176 | SST Anomaly near-real-time (EIC) | 902 frames 4096x2048, daily, MUR SST; Mediterranean visible |
| 5480 / 5046 | Sea ice | Unverified |
| 5234 / 5196 | CO₂ (AIRS monthly; DYAMOND) | Seasonal "breathing" rhythm |
| 5221 | Global mean sea level 1993–2023 | Unverified; good drone layer |
| 5147–5154 | GEOS-FP/CF forecasts (temp, wind, PM2.5…) | Other teams already use these |

## Numeric data (drive the sound with this)
- GISTEMP v4 global monthly/annual CSV: https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv (anomaly vs 1951–1980)
- Zonal annual means: `ZonAnn.Ts+dSST.csv` (latitude bands → separate voices)
- Gridded netCDF 2°x2°: `gistemp1200_GHCNv4_ERSSTv5.nc.gz` (Barcelona cell)
- Others: MUR SST (PO.DAAC), NSIDC Sea Ice Index, NASA POWER API (point climate)

## GIBS / Worldview (live imagery)
- WMS: https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi (GDAL / OWSLib)
- Machine-readable colormaps (RGB → value): https://gibs.earthdata.nasa.gov/colormaps/v1.3/
- Required acknowledgement: "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)."

## Licensing
- SVS products are free to download; follow NASA media usage guidelines.
- Do not use the NASA logo/insignia or imply endorsement.
- Credit "NASA Scientific Visualization Studio" + data sources. GISTEMP is public domain (CC0 on Zenodo).
- Citation: "GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4."

## Colormap inversion (for "any frame" / hover mode)
1. Crop or regenerate the colorbar (SVS colorbar PNG, "vik" colormap, or GIBS XML/JSON).
2. Sample N colours with known values → lookup table.
3. Convert LUT + pixels to CIELAB; nearest neighbour (scipy cKDTree, or precomputed 32³ RGB→value cube in the browser).
4. Reject pixels with ΔE above threshold (land mask, coastlines, labels, compression artefacts).
5. Mask burned-in overlays (date stamp, logos).
6. Validate: per-frame global mean of inverted field vs GISTEMP CSV → correlation plot for the Validity slide.
