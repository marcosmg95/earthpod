# Downloads the large NASA files into .\raw  (run from PowerShell in this folder)
#   Right-click > "Run with PowerShell", or:  powershell -ExecutionPolicy Bypass -File .\download_data.ps1
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # much faster Invoke-WebRequest
$raw = Join-Path $PSScriptRoot "raw"
New-Item -ItemType Directory -Force -Path $raw | Out-Null

$svs = "https://svs.gsfc.nasa.gov/vis/a000000/a005400/a005450"
$svs5313 = "https://svs.gsfc.nasa.gov/vis/a000000/a005300/a005313"
$files = @(
  # GISTEMP v4 gridded anomalies, 2x2 deg, monthly (~26 MB) -> Barcelona-region cell
  @{u="https://data.giss.nasa.gov/pub/gistemp/gistemp1200_GHCNv4_ERSSTv5.nc.gz"; f="gistemp1200_GHCNv4_ERSSTv5.nc.gz"},
  # Hemispheric tables
  @{u="https://data.giss.nasa.gov/gistemp/tabledata_v4/NH.Ts+dSST.csv"; f="NH.Ts+dSST.csv"},
  @{u="https://data.giss.nasa.gov/gistemp/tabledata_v4/SH.Ts+dSST.csv"; f="SH.Ts+dSST.csv"},
  # SVS 5450 Global Temperature Anomalies 1880-2024: equirectangular SOS movie (~90 MB, 900 frames)
  @{u="$svs/2024GISTEMP_MapSOS_h264.mp4"; f="svs5450_SOS_4096x2048.mp4"},
  # Frame -> year mapping (900 lines) and colorbars (for colormap inversion)
  @{u="$svs/time.txt"; f="svs5450_time.txt"},
  @{u="$svs/SOS_GlobalTemperatures_cbar_1000px.png"; f="svs5450_cbar_1000px.png"},
  @{u="$svs/giss_navy_anomaly_Vertical-both.png"; f="svs5450_cbar_vertical.png"},
  # Two full-res PNG frames for validating the inversion (6.4 MB each)
  @{u="$svs/frames/4096x2048_2x1_30p/2024GISTEMP_SOS000.png"; f="svs5450_frame000.png"},
  @{u="$svs/frames/4096x2048_2x1_30p/2024GISTEMP_SOS850.png"; f="svs5450_frame850.png"},
  # SVS 5313 Change in Night Lights 2012-2023, EIC 32:9 version (H.265 - re-encode to H.264 for browsers)
  @{u="$svs5313/nightlights_flat_series_and_change_wZooms_13_EIC_2160p30_h265.mp4"; f="svs5313_EIC_2160p30_h265.mp4"},
  @{u="$svs5313/nightlights_flat_series_and_change_wZooms_13_EIC.02599_print.jpg"; f="svs5313_print.jpg"}
)

foreach ($x in $files) {
  $out = Join-Path $raw $x.f
  if (Test-Path $out) { Write-Host "skip  $($x.f)"; continue }
  Write-Host "get   $($x.f)"
  Invoke-WebRequest -Uri $x.u -OutFile $out -UseBasicParsing
}
Write-Host "`nDone. Files in $raw"
