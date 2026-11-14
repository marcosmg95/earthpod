# Downloads NASA Black Marble VNP46A4 (VIIRS yearly night lights, collection 5200, v002) tiles into .\raw\blackmarble
# These are the annual composites behind SVS 5313 ("Change in Night Lights between 2012 and 2023").
#
# Needs a free Earthdata Login + LAADS download token (never commit it):
#   1. Account:  https://urs.earthdata.nasa.gov/users/new
#   2. Token:    https://ladsweb.modaps.eosdis.nasa.gov/  -> Login -> "Generate Token"
#   3. Run:      $env:EARTHDATA_TOKEN = "<paste token>"
#                powershell -ExecutionPolicy Bypass -File .\download_blackmarble.ps1
#
# Each tile is ~130-140 MB, so the default (Barcelona tile, 2012-2023) is ~1.6 GB.
# Optional extra tiles, matching the SVS 5313 zooms:  -Tiles h18v04,h21v03,h25v06   (Barcelona, Kyiv, Delhi)
param(
  [string[]]$Tiles = @("h18v04"),
  [int]$FirstYear = 2012,
  [int]$LastYear = 2023
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # much faster Invoke-WebRequest

$token = $env:EARTHDATA_TOKEN
if (-not $token) { throw "Set `$env:EARTHDATA_TOKEN first (see the header of this script)." }
$headers = @{ Authorization = "Bearer $token" }

$base = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/VNP46A4"
$out = Join-Path $PSScriptRoot "raw\blackmarble"
New-Item -ItemType Directory -Force -Path $out | Out-Null

foreach ($year in $FirstYear..$LastYear) {
  # Directory listing is public; file names carry a processing timestamp, so look them up.
  $listing = Invoke-RestMethod -Uri "$base/$year/001.json"
  foreach ($tile in $Tiles) {
    $entry = $listing.content | Where-Object { $_.name -like "VNP46A4.A${year}001.$tile.*.h5" } | Select-Object -First 1
    if (-not $entry) { Write-Warning "no file for $tile $year"; continue }
    $dest = Join-Path $out $entry.name
    if (Test-Path $dest) { Write-Host "skip  $($entry.name)"; continue }
    $mb = [math]::Round($entry.size / 1MB)
    Write-Host "get   $($entry.name)  ($mb MB)"
    $part = "$dest.part"
    foreach ($try in 1..3) {   # LAADS sometimes returns a transient 404/5xx
      try { Invoke-WebRequest -Uri $entry.downloadsLink -Headers $headers -OutFile $part -UseBasicParsing; break }
      catch {
        if ($try -eq 3) { throw }
        Write-Warning "attempt $try failed ($($_.Exception.Message)); retrying in 15 s"
        Start-Sleep -Seconds 15
      }
    }
    # A bad/expired token returns an HTML login page instead of HDF5: check the file signature.
    $fs = [System.IO.File]::OpenRead($part)
    try { $sig = New-Object byte[] 4; [void]$fs.Read($sig, 0, 4) } finally { $fs.Close() }
    if ([System.Text.Encoding]::ASCII.GetString($sig, 1, 3) -ne "HDF") {
      Remove-Item $part
      throw "Download of $($entry.name) is not HDF5 - check EARTHDATA_TOKEN (expired or wrong?)."
    }
    Move-Item $part $dest
  }
}
Write-Host "`nDone. Files in $out"
Write-Host "Next (from backend\): uv run --extra blackmarble python scripts\poc5_blackmarble_regions.py"
