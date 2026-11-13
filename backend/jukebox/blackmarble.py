"""NASA Black Marble VNP46A4 (VIIRS yearly night lights) -> per-region yearly radiance.

Tiles are 10x10 deg on a lat/lon grid (2400x2400 px, 15 arc-seconds). Tile hXXvYY has its
upper-left corner at lon = -180 + 10*h, lat = 90 - 10*v. Radiance is in nW/cm^2/sr.
h5py is imported lazily so the geometry helpers (and their tests) need no HDF5 stack.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

TILE_DEG = 10.0
DEFAULT_LAYER = "AllAngle_Composite_Snow_Free"  # the standard yearly composite


@dataclass(frozen=True)
class Region:
    key: str
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    @property
    def tile(self) -> str:
        return tile_for(0.5 * (self.lat_min + self.lat_max), 0.5 * (self.lon_min + self.lon_max))


# Metro-area boxes. Barcelona is the local track; Kyiv and Delhi match the SVS 5313 zooms.
REGIONS = {
    "barcelona": Region("barcelona", "Barcelona metro area", 41.25, 41.60, 1.90, 2.35),
    "kyiv": Region("kyiv", "Kyiv", 50.25, 50.65, 30.20, 30.85),
    "delhi": Region("delhi", "Delhi", 28.40, 28.90, 76.80, 77.50),
}


def tile_for(lat: float, lon: float) -> str:
    h = int(math.floor((lon + 180.0) / TILE_DEG))
    v = int(math.floor((90.0 - lat) / TILE_DEG))
    return f"h{h:02d}v{v:02d}"


def tile_origin(tile: str) -> tuple[float, float]:
    """(lat_top, lon_left) of a tile like 'h18v04'."""
    m = re.fullmatch(r"h(\d{2})v(\d{2})", tile)
    if not m:
        raise ValueError(f"bad tile id: {tile!r}")
    h, v = int(m.group(1)), int(m.group(2))
    return 90.0 - TILE_DEG * v, -180.0 + TILE_DEG * h


def pixel_window(region: Region, tile: str, n_rows: int, n_cols: int) -> tuple[slice, slice]:
    """Row/col slices of `region` inside `tile` (rows run north -> south)."""
    lat_top, lon_left = tile_origin(tile)
    dy, dx = TILE_DEG / n_rows, TILE_DEG / n_cols
    def px(x):  # round away float noise (8.4 * 240 -> 2015.9999...) before floor/ceil
        return round(x, 6)

    r0 = max(0, int(math.floor(px((lat_top - region.lat_max) / dy))))
    r1 = min(n_rows, int(math.ceil(px((lat_top - region.lat_min) / dy))))
    c0 = max(0, int(math.floor(px((region.lon_min - lon_left) / dx))))
    c1 = min(n_cols, int(math.ceil(px((region.lon_max - lon_left) / dx))))
    if r0 >= r1 or c0 >= c1:
        raise ValueError(f"region {region.key} is not inside tile {tile}")
    return slice(r0, r1), slice(c0, c1)


def parse_name(path: Path) -> tuple[int, str]:
    """'VNP46A4.A2012001.h18v04.002.<ts>.h5' -> (2012, 'h18v04')."""
    m = re.match(r"VNP46A4\.A(\d{4})\d{3}\.(h\d{2}v\d{2})\.", path.name)
    if not m:
        raise ValueError(f"not a VNP46A4 file: {path.name}")
    return int(m.group(1)), m.group(2)


def _find_dataset(h5, name: str):
    found = []
    h5.visititems(lambda p, obj: found.append(p) if p.split("/")[-1] == name else None)
    if not found:
        raise KeyError(f"dataset {name!r} not found")
    return h5[found[0]]


def _attr(ds, key, default):
    v = ds.attrs.get(key, default)
    try:
        return float(v[0]) if hasattr(v, "__len__") else float(v)
    except (TypeError, ValueError):
        return default


def region_stats(path: Path, region: Region, layer: str = DEFAULT_LAYER) -> dict:
    """Radiance stats for one region in one VNP46A4 file (fill pixels excluded)."""
    import h5py
    import numpy as np

    year, tile = parse_name(path)
    with h5py.File(path, "r") as f:
        ds = _find_dataset(f, layer)
        rows, cols = pixel_window(region, tile, *ds.shape)
        raw = ds[rows, cols].astype("float64")
        fill = _attr(ds, "_FillValue", 65535.0)
        scale = _attr(ds, "scale_factor", 0.1)
        offset = _attr(ds, "add_offset", 0.0)
    valid = raw != fill
    rad = raw[valid] * scale + offset
    return {
        "region": region.key, "year": year, "tile": tile, "layer": layer,
        "mean_radiance": float(rad.mean()) if rad.size else float("nan"),
        "median_radiance": float(np.median(rad)) if rad.size else float("nan"),
        "sum_radiance": float(rad.sum()),   # "sum of lights", insensitive to dark sea pixels
        "valid_px": int(valid.sum()), "total_px": int(valid.size),
    }
