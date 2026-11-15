"""PoC 4 — Barcelona-region annual anomaly from the GISTEMP 2x2 deg grid.

Needs data/raw/gistemp1200_GHCNv4_ERSSTv5.nc.gz (backend/data/download_data.ps1) and
`uv sync --extra netcdf`. Writes data/derived/barcelona_annual.csv
(read by jukebox.data.load_barcelona_annual).

    uv run python scripts/poc4_barcelona.py                 # nearest cell to Barcelona
    uv run python scripts/poc4_barcelona.py --neighbors 1   # 3x3 cells (~600 km, NE Iberia + sea)
"""
import argparse
import gzip
import shutil
import sys


import numpy as np
import pandas as pd

from jukebox import paths

BCN = (41.39, 2.17)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=BCN[0])
    ap.add_argument("--lon", type=float, default=BCN[1])
    ap.add_argument("--neighbors", type=int, default=0)
    ap.add_argument("--min-months", type=int, default=10)
    a = ap.parse_args()

    gz = paths.RAW_DIR / "gistemp1200_GHCNv4_ERSSTv5.nc.gz"
    nc = gz.with_suffix("")
    if not nc.exists():
        if not gz.exists():
            sys.exit("Missing gridded file. Run backend/data/download_data.ps1 first.")
        with gzip.open(gz, "rb") as fi, open(nc, "wb") as fo:
            shutil.copyfileobj(fi, fo)
    try:
        import netCDF4
    except ImportError:
        sys.exit("Install netCDF4 first:  uv sync --extra netcdf")

    ds = netCDF4.Dataset(nc)
    lat, lon = ds["lat"][:], ds["lon"][:]
    i, j = int(np.abs(lat - a.lat).argmin()), int(np.abs(lon - a.lon).argmin())
    k = a.neighbors
    block = ds["tempanomaly"][:, max(0, i - k):i + k + 1, max(0, j - k):j + k + 1]
    series = np.ma.filled(block.astype(float), np.nan)
    monthly = np.nanmean(series.reshape(series.shape[0], -1), axis=1)
    times = netCDF4.num2date(ds["time"][:], ds["time"].units, only_use_cftime_datetimes=False)
    m = pd.Series(monthly, index=pd.DatetimeIndex([pd.Timestamp(str(t)[:10]) for t in times]))
    g = m.groupby(m.index.year)
    annual = g.mean()[g.count() >= a.min_months]

    out = paths.DERIVED_DIR / "barcelona_annual.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"Year": annual.index, "anomaly": annual.round(3).values}).to_csv(out, index=False)
    print(f"Cell centre(s) around {float(lat[i]):.0f}N {float(lon[j]):.0f}E (+-{k} cells)")
    print(f"{len(annual)} years, {annual.index.min()}-{annual.index.max()}; "
          f"last 5-yr mean {annual.tail(5).mean():+.2f} degC vs 1951-1980")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
