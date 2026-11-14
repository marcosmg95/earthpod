"""SVS 5011 — Lightning events detected from the ISS (LIS), 2017–2023, Science On a Sphere version.

An equirectangular map (180°W at the left edge, north at the top): yellow dots are lightning flashes seen by
the Lightning Imaging Sensor in a 10-day roving window, over a dark Earth. Movie: 100 s at 60 fps.
The movie prints no dates and its storms swing between the hemispheres every ~720 frames (12 s), 7.7 times
over the active part — more cycles than the page's 2017–2023 span — so frames are not given calendar dates:
each is labelled with the season the map shows (more lightning north or south of the equator).

    table   flashes   share of the map covered by yellow dots (all lightning on screen)
            north     share of those in the northern hemisphere, 0..1
            x, lat    centre of the lightning: 0 (left, 180°W) .. 1 (right), latitude -90..90
            new       share of the map where a dot appears that was not there the frame before (new flashes)
            americas / africa_europe / asia_oceania   lightning in three longitude bands, same unit as flashes
    arrays  grid      (frames, ROWS, COLS) lightning per 10° x 10° cell, 0..1 (cell share, x GRID_GAIN)

Picture indices: dot coverage on the rendered map, not flash counts or rates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import block_mean, frames, hsv

MOVIE = "iss_lightning_sos_yearly_07312023_2048p60.mp4"
URL = "https://svs.gsfc.nasa.gov/vis/a000000/a005000/a005011/" + MOVIE
FPS = 60.0
SIZE = (1440, 720)
ROWS, COLS = 18, 36
GRID_GAIN = 10.0               # dots rarely cover more than a tenth of a cell: scale so a busy cell is ~1
BANDS = {"americas": (-170, -30), "africa_europe": (-30, 60), "asia_oceania": (60, 180)}
SEASON_SMOOTH = 61             # frames (1 s) of smoothing before naming the season
CHAPTERS: list = []
NOTES = __doc__


def season(north: float, flashes: float) -> str:
    if flashes < 0.0005:
        return "few storms on the map"
    if north > 0.65:
        return "northern storm season"
    if north < 0.35:
        return "southern storm season"
    return "storms on both sides of the equator"


def labels(table: pd.DataFrame) -> list[str]:
    north = table.north.rolling(SEASON_SMOOTH, center=True, min_periods=1).mean()
    flashes = table.flashes.rolling(SEASON_SMOOTH, center=True, min_periods=1).mean()
    return [season(n, f) for n, f in zip(north, flashes)]


def dots(bgr: np.ndarray) -> np.ndarray:
    hue, sat, val = hsv(bgr)
    return ((hue >= 40) & (hue < 70) & (sat > 0.45) & (val > 0.45)).astype(np.float32)


def extract(path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    w, h = SIZE
    lon = -180 + (np.arange(w) + 0.5) * 360 / w
    lat = 90 - (np.arange(h) + 0.5) * 180 / h
    rows, grids, prev = [], [], None
    for _, bgr in frames(path, SIZE):
        d = dots(bgr)
        total = d.sum()
        colsum, rowsum = d.sum(axis=0), d.sum(axis=1)
        row = dict(flashes=d.mean(), north=rowsum[lat > 0].sum() / total if total else 0.5,
                   x=float((colsum * (np.arange(w) + 0.5) / w).sum() / total) if total else 0.5,
                   lat=float((rowsum * lat).sum() / total) if total else 0.0,
                   new=float((d * (1 - prev)).mean()) if prev is not None else 0.0)
        for name, (a, b) in BANDS.items():
            row[name] = colsum[(lon >= a) & (lon < b)].sum() / d.size
        rows.append(row)
        grids.append(np.clip(block_mean(d, ROWS, COLS) * GRID_GAIN, 0, 1))
        prev = d
    return pd.DataFrame(rows), {"grid": np.array(grids)}
