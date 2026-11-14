"""SVS 3912 — Global sea surface currents and temperature (ECCO2 model), flat map, 67 s at 30 fps.

Short streaks follow the surface currents and are coloured by sea surface temperature: blue / cyan = cold,
green, yellow, orange, red = warm. Land is flat grey. Equirectangular, 180°W at the left edge, north at the
top. The page gives no dates for the frames, so they are labelled by frame number.

    table   temp      mean temperature index of the streaks, 0 (blue, cold) .. 1 (red, warm)
            warm      share of the ocean drawn red / orange (index > 0.8)
            motion    how much the streaks change from the previous frame (flow activity), 0..1
            <basin>_motion, <basin>_temp   the same inside the Pacific, Atlantic and Indian Ocean boxes
            fast_x, fast_lat   where the motion is concentrated (0..1 from the left, latitude)
    arrays  temp      (frames, ROWS, COLS) temperature index per 10° cell (0 where there is no ocean)
            motion    (frames, ROWS, COLS) flow activity per cell, 0..1 (x MOTION_GAIN)

Picture indices: hue of the colour scale and pixel change, not °C or m/s.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import block_mean, frames, hsv

MOVIE = "ecco2_sst_flow.mp4"
URL = "https://svs.gsfc.nasa.gov/vis/a000000/a003900/a003912/" + MOVIE
FPS = 30.0
SIZE = (1080, 540)
ROWS, COLS = 18, 36
MOTION_GAIN = 4.0
# (lon0, lon1, lat0, lat1) boxes; the Pacific crosses the date line
BASINS = {"pacific": [(120, 180, -60, 60), (-180, -80, -60, 60)], "atlantic": [(-80, 20, -60, 65)],
          "indian": [(20, 120, -60, 25)]}
CHAPTERS: list = []
NOTES = __doc__


def labels(table: pd.DataFrame) -> list[str]:
    return [f"frame {i + 1:04d}" for i in range(len(table))]


def temperature(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(streak mask, temperature index 0..1) per pixel."""
    hue, sat, val = hsv(bgr)
    streak = (sat > 0.35) & (val > 0.2) & (hue <= 250)
    return streak, (1 - np.clip(hue, 0, 240) / 240) * streak


def _box_mask(shape) -> dict[str, np.ndarray]:
    h, w = shape
    lon = -180 + (np.arange(w) + 0.5) * 360 / w
    lat = 90 - (np.arange(h) + 0.5) * 180 / h
    out = {}
    for name, boxes in BASINS.items():
        m = np.zeros((h, w), bool)
        for a, b, c, d in boxes:
            m |= ((lon >= a) & (lon < b))[None, :] & ((lat >= c) & (lat < d))[:, None]
        out[name] = m
    return out


def extract(path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    w, h = SIZE
    boxes = _box_mask((h, w))
    lat = 90 - (np.arange(h) + 0.5) * 180 / h
    rows, temps, motions, prev = [], [], [], None
    for _, bgr in frames(path, SIZE):
        streak, temp = temperature(bgr)
        val = hsv(bgr)[2]
        move = np.abs(val - prev) if prev is not None else np.zeros_like(val)
        n = max(streak.sum(), 1)
        row = dict(temp=temp.sum() / n, warm=(temp > 0.8).sum() / n, motion=float(move.mean() * MOTION_GAIN))
        for name, m in boxes.items():
            row[f"{name}_motion"] = float(move[m].mean() * MOTION_GAIN)
            row[f"{name}_temp"] = float(temp[m].sum() / max(streak[m].sum(), 1))
        total = move.sum()
        row["fast_x"] = float((move.sum(axis=0) * (np.arange(w) + 0.5) / w).sum() / total) if total else 0.5
        row["fast_lat"] = float((move.sum(axis=1) * lat).sum() / total) if total else 0.0
        rows.append(row)
        cover = block_mean(streak.astype(np.float32), ROWS, COLS)
        temps.append(np.where(cover > 0.02, block_mean(temp, ROWS, COLS) / np.maximum(cover, 1e-6), 0))
        motions.append(np.clip(block_mean(move, ROWS, COLS) * MOTION_GAIN, 0, 1))
        prev = val
    return pd.DataFrame(rows), {"temp": np.clip(np.array(temps), 0, 1), "motion": np.array(motions)}
