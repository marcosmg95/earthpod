# 02 — Data sources

## Sources in the production web app

The current web app contains two chapters:

- **The breathing planet:** NASA Scientific Visualization Studio (SVS) 5196, DYAMOND Global Carbon Dioxide, January–March 2020. The sonification follows features measured from the visualization; it is not a calibrated CO₂ dataset.
- **The night lights:** NASA SVS 5313, Change in Night Lights 2012–2023 — EIC Version. The sonification follows image features and the on-screen sequence; it is not a calibrated radiance product.

EarthPod credits NASA SVS and does not imply NASA endorsement. Other datasets and pages listed below support backend research and demos; they are not all chapters in the production web app.

## NASA SVS (where EIC visuals live)
- EIC gallery: https://svs.gsfc.nasa.gov/gallery/earth-information-center/
- Earth Now dashboard: https://svs.gsfc.nasa.gov/gallery/earth-now-dashboard/
- Daily visualizations: https://svs.gsfc.nasa.gov/gallery/whats-newwith-earth-today/
- Formats: MP4/WebM + frame directories (TIF/EXR, often PNG/JPG). Frame ranges downloadable with curl, e.g.
  `curl -LO "https://svs.gsfc.nasa.gov/vis/.../frames/1024x512/name.[0060-0119].png"`

### The challenge's Resources tab (read 14 Nov 2026)
https://www.spaceappschallenge.org/2026/challenges/the-earth-information-jukebox/?tab=resources — besides the EIC
gallery, it lists these SVS pages. All are measured and sonified in this repo (`backend/README.md` → "The other pages
on the challenge's Resources tab"); 13786 is only a sonification example.

| SVS ID | Resource | What we use |
|---|---|---|
| 13786 | Data Sonification: Caldwell 73 | reference only (luminosity → volume, position → pitch) |
| 5313 | Change in Night Lights 2012–2023 – EIC Version | EIC movie (32:9, H.265); `svs5313/` scripts; Black Marble VNP46A4 numbers (PoC 5) |
| 5196 | DYAMOND Global Carbon Dioxide | 1080p movies; `svs5196/co2_*` |
| 5669 | GEOS Aerosols (2025) | the **still** map (19 Aug 2025 20:00 UTC) scanned west → east; `svs5669/aerosols_scan`, `svs5669/aerosols_bands` |
| 5533 | Air Quality Model Runs (GEOS-CF) | `EIC_AirQuality_Preview_3840x1080.mp4`; `svs5533/pollutant_quartet` |
| 5011 | Lightning Events Detected from the ISS 2017–2023 | SOS map movie (4096x2048, 60 fps); `svs5011/storm_map` |
| 3912 | Global Sea Surface Currents and Temperature (ECCO2) | `ecco2_sst_flow.mp4` flat map; `svs3912/warm_and_cold_currents` |
| 5425 | Perpetual Ocean 2: Western Boundary Currents | 1080p "clean, no date" movie (317 s) + dates-only movie; `svs5425/boundary_currents` |
| 4960 | A 3D View of an Atmospheric River from an Earth System Model | `atmos_river_HD.mp4` (292 s) + dates-only movie; `svs4960/river_rain_clock` |
| 4950 | GEDI Forest Height | `GEDI_global_w_colorbar_1080p60.mp4`; `svs4950/forest_meridian` |

SVS 5450 (GISTEMP temperature anomalies) is **not** on the Resources tab and is no longer used for the submission;
its demo script and PoCs 1, 3 and 4 stay in the repo. Other pages we looked at earlier (5176 SST anomaly, sea ice, sea level,
GEOS-FP forecasts 5147–5154) are not on the tab either.

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
