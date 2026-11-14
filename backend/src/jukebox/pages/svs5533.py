"""SVS 5533 — Air Quality Model Runs (GEOS-CF), EIC 32:9 version: four pollutants side by side.

The movie is one equirectangular world map cut into eight vertical panels, two runs of
carbon monoxide (CO) · fine particles (PM2.5) · nitrogen oxides (NOx) · ozone (O3), each panel in its
own colour scale (light = low, dark = high). The strip drifts slowly sideways while the model runs.

Each screen column is assigned to a pollutant by its colour (hue, and saturation to tell the cream PM2.5
panels from the yellow-orange CO ones), then each pixel's darkness inside its panel (CIELAB L*) gives a
concentration index 0..1. Washed-out pixels (ice, grey / black no-data areas, labels) count as 0.

    table   <p>       mean index over that pollutant's panels, 0..1      (p = co, pm25, nox, o3)
            <p>_peak  95th percentile of the index (the darkest plumes)
            <p>_x     where its index is concentrated on screen, 0 (left) .. 1 (right)
            <p>_lat   latitude of that centre of mass, -90..90
            <p>_cols  share of the screen width its panels cover
            centre    pollutant of the panel at the middle of the screen
    arrays  <p>       (frames, ROWS) mean index per latitude band, north first

Picture indices from the colour scales, not ppb or µg/m³.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import frames, hsv, lightness

MOVIE = "EIC_AirQuality_Preview_3840x1080.mp4"
URL = "https://svs.gsfc.nasa.gov/vis/a000000/a005500/a005533/" + MOVIE
FPS = 60.0
SIZE = (960, 270)
ROWS = 18
PANEL = 125                        # panel width in pixels at SIZE (the screen shows ~7.7 panels)
LABEL_ROWS = (0.80, 0.90)          # the pollutant name boxes
POLLUTANTS = ("co", "pm25", "nox", "o3")
NAMES = {"co": "carbon monoxide", "pm25": "fine particles (PM2.5)", "nox": "nitrogen oxides",
         "o3": "ozone"}
# L* of the lightest (low) and darkest (high) end of each colour scale
L_RANGE = {"co": (90, 35), "pm25": (95, 35), "nox": (90, 37), "o3": (78, 26)}
# the panel at the middle of the screen (measured: the strip moves one panel every ~15 s)
CHAPTERS = [("Ozone", 0), ("Carbon monoxide", 140), ("Fine particles", 1044), ("Nitrogen oxides", 1944),
            ("Ozone again", 2850), ("Carbon monoxide again", 3738)]
NOTES = __doc__


def classify_columns(hue: np.ndarray, sat: np.ndarray) -> np.ndarray:
    """Pollutant index (0..3) of each screen column, -1 if unclear."""
    colour = sat > 0.15
    n = colour.sum(axis=0).clip(1)
    sin = (np.sin(np.radians(hue)) * colour).sum(axis=0) / n
    cos = (np.cos(np.radians(hue)) * colour).sum(axis=0) / n
    h = np.degrees(np.arctan2(sin, cos)) % 360                   # circular mean hue per column
    s = np.median(sat, axis=0)
    kind = np.full(hue.shape[1], -1)
    kind[(h >= 25) & (h < 70) & (s >= 0.47)] = 0                 # CO: yellow-orange
    kind[(h >= 25) & (h < 70) & (s < 0.47)] = 1                  # PM2.5: cream
    kind[(h >= 90) & (h < 160)] = 2                              # NOx: green
    kind[(h >= 220) & (h < 300)] = 3                             # O3: violet
    # majority vote over neighbouring columns: panel edges and plumes do not flip a column
    votes = np.stack([np.convolve(kind == k, np.ones(9), mode="same") for k in range(4)])
    kind = np.where(votes.max(axis=0) > 0, votes.argmax(axis=0), -1)
    return split_orange(kind, s, PANEL * hue.shape[1] / SIZE[0])


def split_orange(kind: np.ndarray, sat: np.ndarray, panel: float) -> np.ndarray:
    """CO and PM2.5 share a hue, and dark PM2.5 plumes are as saturated as CO: split each orange run by the
    fixed panel order instead (... O3 | CO | PM2.5 | NOx ...), one panel width per pollutant."""
    kind = kind.copy()
    orange = np.isin(kind, (0, 1))
    w, x = len(kind), 0
    while x < w:
        if not orange[x]:
            x += 1
            continue
        b = x
        while b < w and orange[b]:
            b += 1
        left = kind[x - 1] if x > 0 else None
        right = kind[b] if b < w else None
        if right == 2:                          # NOx follows: the last panel width is PM2.5
            cut = max(x, int(round(b - panel)))
        elif left == 3:                         # O3 precedes: the first panel width is CO
            cut = min(b, int(round(x + panel)))
        else:                                   # neither neighbour on screen: go by saturation
            cut = x if np.median(sat[x:b]) < 0.47 else b
        kind[x:cut], kind[cut:b] = 0, 1
        x = b
    return kind


def measure(bgr: np.ndarray) -> tuple[dict, dict]:
    hue, sat, _ = hsv(bgr)
    L = lightness(bgr)
    h, w = L.shape
    kind = classify_columns(hue, sat)
    keep = np.ones((h, w), bool)
    keep[int(LABEL_ROWS[0] * h):int(LABEL_ROWS[1] * h)] = False
    lat = 90 - (np.arange(h) + 0.5) * 180 / h
    band = np.minimum((np.arange(h) * ROWS) // h, ROWS - 1)
    row, rows = {}, {}
    for k, p in enumerate(POLLUTANTS):
        cols = kind == k
        lo, hi = L_RANGE[p]
        idx = np.clip((lo - L) / (lo - hi), 0, 1) * (sat > 0.15) * keep
        idx = idx * cols[None, :]
        ncols = int(cols.sum())
        mean = idx.sum() / max(ncols * h, 1)
        total = idx.sum()
        row[p] = mean
        row[f"{p}_peak"] = float(np.percentile(idx[:, cols], 95)) if ncols else 0.0
        row[f"{p}_x"] = float((idx.sum(axis=0) * (np.arange(w) + 0.5) / w).sum() / total) if total else 0.5
        row[f"{p}_lat"] = float((idx.sum(axis=1) * lat).sum() / total) if total else 0.0
        row[f"{p}_cols"] = ncols / w
        rows[p] = np.bincount(band, weights=idx.sum(axis=1), minlength=ROWS) / max(ncols * h / ROWS, 1)
    centre = int(np.bincount(kind[w // 2 - 5:w // 2 + 5].clip(0), minlength=4).argmax())
    row["centre"] = POLLUTANTS[centre]
    return row, rows


def labels(table: pd.DataFrame) -> list[str]:
    return [f"centre: {NAMES[p]}" for p in table.centre]


def extract(path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    rows, arrays = [], {p: [] for p in POLLUTANTS}
    for _, bgr in frames(path, SIZE):
        row, prof = measure(bgr)
        rows.append(row)
        for p in POLLUTANTS:
            arrays[p].append(prof[p])
    return pd.DataFrame(rows), {p: np.clip(np.array(a), 0, 1) for p, a in arrays.items()}
