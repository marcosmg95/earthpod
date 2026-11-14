"""SVS 4950 — GEDI Forest Height: the globe turns once (51 s at 60 fps), forests drawn as extruded colour.

Colour bar "Height Above Ground": brown and dark olive = short vegetation, bright green and white = tall
forest. The camera faces longitude ~140°E at frame 0 and the globe turns westward through the movie
(Asia, Africa, the Americas, the Pacific), so the meridian at the centre of the disk sweeps the planet.

    table   land      share of the visible disk that is land (not ocean blue)
            canopy    mean canopy index over that land, 0 (brown) .. 1 (bright green / white)
            tall      share of the disk where the canopy index is high (> TALL)
            tall_x    horizontal centre of that tall forest, -1 (left) .. +1 (right of the disk)
            lon       longitude facing the camera (degrees, east positive)
    arrays  meridian  (frames, ROWS) canopy index along the central meridian strip, north first
            land_rows (frames, ROWS) land share along that strip

Picture indices from colour and brightness (the height is exaggerated and lit by a virtual sun), not metres.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import frames, hsv, lon_label

MOVIE = "GEDI_global_w_colorbar_1080p60.mp4"
URL = "https://svs.gsfc.nasa.gov/vis/a000000/a004900/a004950/" + MOVIE
FPS = 60.0
FRAMES = 3089
SIZE = (960, 540)
CENTER, RADIUS = (480, 270), 262       # the globe's disk at SIZE (measured from the movie)
COLORBAR = (0, 0.86, 0.28, 1.0)        # x0, y0, x1, y1 fractions: colour bar, bottom left
LON0 = 140.0                           # longitude facing the camera at frame 0
ROWS = 18                              # latitude bands along the meridian strip (~10 degrees each)
STRIP = 0.06                           # half width of the meridian strip, in disk radii
TALL = 0.6
CHAPTERS = [("Asia and Australia", 0), ("Indian Ocean", 560), ("Africa and Europe", 1000),
            ("South America", 1500), ("North America", 1900), ("Pacific", 2350)]
NOTES = __doc__


def lon_at(frame) -> np.ndarray | float:
    return (LON0 - 360.0 * np.asarray(frame) / FRAMES + 180) % 360 - 180


def labels(table: pd.DataFrame) -> list[str]:
    n = len(table)
    return [f"facing {lon_label(float(lon_at(i)))}" for i in range(n)]


def canopy(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(land mask, canopy index 0..1) per pixel."""
    hue, sat, val = hsv(bgr)
    ocean = (hue > 185) & (hue < 230) & (sat > 0.3)
    land = (val > 0.08) & ~ocean
    green = np.clip((hue - 40) / 25, 0, 1) * (hue < 130)
    white = (sat < 0.2) & (val > 0.7)
    index = np.clip((val - 0.2) / 0.55, 0, 1) * np.maximum(green, white)
    return land, index * land


def _geometry():
    w, h = SIZE
    ys, xs = np.mgrid[0:h, 0:w]
    dx, dy = (xs - CENTER[0]) / RADIUS, (CENTER[1] - ys) / RADIUS
    disk = dx ** 2 + dy ** 2 < 0.97 ** 2
    x0, y0, x1, y1 = COLORBAR
    disk &= ~((xs >= x0 * w) & (xs < x1 * w) & (ys >= y0 * h) & (ys < y1 * h))
    lat = np.degrees(np.arcsin(np.clip(dy, -1, 1)))
    band = np.clip(((90 - lat) / 180 * ROWS).astype(int), 0, ROWS - 1)
    strip = disk & (np.abs(dx) < STRIP)
    return disk, dx, band, strip


def extract(path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    disk, dx, band, strip = _geometry()
    sband = band[strip]
    count = np.bincount(sband, minlength=ROWS).clip(1)
    rows, meridian, land_rows = [], [], []
    for _, bgr in frames(path, SIZE):
        land, index = canopy(bgr)
        dl, di = land & disk, index * disk
        tall = di > TALL
        n_tall = tall.sum()
        rows.append(dict(land=dl.sum() / disk.sum(), canopy=di.sum() / max(dl.sum(), 1),
                         tall=n_tall / disk.sum(), tall_x=float(dx[tall].mean()) if n_tall else 0.0))
        land_rows.append(np.bincount(sband, weights=land[strip], minlength=ROWS) / count)
        meridian.append(np.bincount(sband, weights=index[strip], minlength=ROWS)
                        / np.bincount(sband, weights=land[strip], minlength=ROWS).clip(1))
    table = pd.DataFrame(rows)
    table["lon"] = lon_at(np.arange(len(table)))
    return table, {"meridian": np.array(meridian), "land_rows": np.array(land_rows)}
