"""Loaders for NASA GISTEMP v4 tables (anomalies in degC vs 1951-1980)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]  # .../backend
DATA_DIR = BACKEND_DIR / "data"
GISTEMP_DIR = DATA_DIR / "gistemp"
RAW_DIR = DATA_DIR / "raw"
DERIVED_DIR = DATA_DIR / "derived"

# ZonAnn column -> friendly voice name
ZONES = {
    "64N-90N": "Arctic",
    "44N-64N": "Northern mid-latitudes",
    "24S-24N": "Tropics",
    "90S-24S": "Southern extratropics",
}


def load_global_monthly(path: Path | None = None) -> pd.DataFrame:
    """GLB.Ts+dSST.csv -> DataFrame indexed by Year (Jan..Dec, annual, seasons)."""
    path = path or GISTEMP_DIR / "GLB.Ts+dSST.csv"
    df = pd.read_csv(path, skiprows=1, na_values=["***", "****"])
    df = df.rename(columns={"J-D": "annual"}).set_index("Year")
    return df.apply(pd.to_numeric, errors="coerce")


def load_global_annual(path: Path | None = None) -> pd.Series:
    """Annual (Jan-Dec) global anomaly; incomplete years dropped."""
    s = load_global_monthly(path)["annual"].dropna()
    s.name = "global"
    return s


def load_zonal_annual(path: Path | None = None) -> pd.DataFrame:
    """ZonAnn.Ts+dSST.csv -> DataFrame indexed by Year (Glob, NHem, ..., 90S-64S)."""
    path = path or GISTEMP_DIR / "ZonAnn.Ts+dSST.csv"
    df = pd.read_csv(path, na_values=["***", "****"]).set_index("Year")
    return df.apply(pd.to_numeric, errors="coerce")


def load_barcelona_annual(path: Path | None = None) -> pd.Series | None:
    """Barcelona-region annual series produced by backend/scripts/poc4_barcelona.py (or None)."""
    path = path or DERIVED_DIR / "barcelona_annual.csv"
    if not Path(path).exists():
        return None
    s = pd.read_csv(path).set_index("Year")["anomaly"].dropna()
    s.name = "barcelona"
    return s


def load_blackmarble_annual(path: Path | None = None) -> pd.DataFrame | None:
    """Night-light % change vs 2012 per region (columns) and year (index), from PoC 5 (or None)."""
    path = path or DERIVED_DIR / "blackmarble_annual.csv"
    if not Path(path).exists():
        return None
    df = pd.read_csv(path)
    return df.pivot(index="year", columns="region", values="pct_change_vs_first").sort_index()


def load_frame_years(path: Path | None = None) -> list[int] | None:
    """SVS 5450 time.txt: one year per movie frame (900 lines)."""
    path = path or RAW_DIR / "svs5450_time.txt"
    if not Path(path).exists():
        return None
    return [int(float(x)) for x in Path(path).read_text().split() if x.strip()]


def frame_for_year(frame_years: list[int], year: int) -> int | None:
    """Index of the middle frame showing `year` (None if the movie never shows it)."""
    idx = [i for i, y in enumerate(frame_years) if y == year]
    return idx[len(idx) // 2] if idx else None
