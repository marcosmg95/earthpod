"""SVS 5669 — GEOS Aerosols (2025): one still map (19 Aug 2025, 20:00 UTC), read as a left-to-right scan.

The image is an equirectangular world map (180°W at the left edge, north at the top) where four aerosol types
are drawn in their own colour over a dark Earth (legend: Aerosols_cbar.png):

    black carbon  red-orange      dust  lilac      sea salt  grey-teal      sulfate  green

The scan crosses the map in STEPS steps of 360/STEPS degrees of longitude, FPS steps per second. For each step
(one vertical strip of the map) and each type: how much of the strip is drawn in that colour, row by row
(ROWS bands of latitude, north first), weighted by how bright and saturated the colour is.

    table: <type> (share of the strip, 0..1), <type>_lat (latitude of its centre of mass, -90..90), lon
    arrays: <type> (steps, ROWS) amount per latitude band, 0..1

Picture indices: colour and brightness of the rendered image, not mass or optical depth.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import block_mean, hsv, lon_label

MOVIE = "Aerosols_2025-08-19T20_00_00_1920x1080.png"
URL = "https://svs.gsfc.nasa.gov/vis/a000000/a005600/a005669/" + MOVIE
STILL = True
STEPS = 480                  # 0.75 degrees of longitude per step
FPS = 10.0                   # steps per second: the scan lasts 48 s
ROWS = 36                    # 5-degree latitude bands, north to south
TYPES = ("black_carbon", "dust", "sea_salt", "sulfate")
NAMES = {"black_carbon": "black carbon", "dust": "dust", "sea_salt": "sea salt", "sulfate": "sulfate"}
CHAPTERS = [("Americas", int(STEPS * (180 - 170) / 360)), ("Atlantic", int(STEPS * (180 - 60) / 360)),
            ("Africa and Europe", int(STEPS * (180 - 20) / 360)), ("Asia", int(STEPS * (180 + 60) / 360)),
            ("Pacific", int(STEPS * (180 + 140) / 360))]
NOTES = __doc__


def lon_of(step: np.ndarray | int) -> np.ndarray | float:
    """Longitude (degrees) at the centre of scan step `step`."""
    return -180 + (np.asarray(step) + 0.5) * 360 / STEPS


def labels(table: pd.DataFrame) -> list[str]:
    return [lon_label(float(lon), step=5) for lon in table.lon]


def layers(bgr: np.ndarray) -> dict[str, np.ndarray]:
    """Per-pixel amount 0..1 of each aerosol colour."""
    hue, sat, val = hsv(bgr)
    ink = np.clip((val - 0.18) / 0.6, 0, 1)                    # dark Earth / night ocean = no aerosol
    return {
        "black_carbon": ink * ((hue < 30) | (hue >= 345)) * (sat > 0.35),
        "dust": ink * ((hue >= 260) & (hue < 345)) * (sat > 0.12),
        "sea_salt": ink * ((hue >= 165) & (hue < 230)) * (sat > 0.06) * (sat < 0.5),
        "sulfate": ink * ((hue >= 75) & (hue < 160)) * (sat > 0.35),
    }


def extract(path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    import cv2

    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    bgr = cv2.resize(bgr, (STEPS * 4, ROWS * 30), interpolation=cv2.INTER_AREA)
    lat = 90 - (np.arange(ROWS) + 0.5) * 180 / ROWS
    rows, arrays = {"lon": lon_of(np.arange(STEPS))}, {}
    for name, layer in layers(bgr).items():
        grid = block_mean(layer, ROWS, STEPS).T                 # (steps, rows)
        arrays[name] = np.clip(grid, 0, 1)
        total = grid.sum(axis=1)
        rows[name] = grid.mean(axis=1)
        rows[f"{name}_lat"] = np.where(total > 0, (grid * lat).sum(axis=1) / np.maximum(total, 1e-9), 0.0)
    return pd.DataFrame(rows), arrays
