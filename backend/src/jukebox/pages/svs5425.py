"""SVS 5425 — Perpetual Ocean 2: Western Boundary Currents (ECCO2 model, 2021–2023). 5 min 17 s at 30 fps.

White streamlines trace surface currents over a blue ocean. The camera turns the globe, then flies to the
Kuroshio off Japan, across the Indian Ocean to the Agulhas Current off South Africa, over the South Atlantic
and Brazil, up the Gulf Stream and the Gulf of Mexico, and back out to the globe. Model time runs steadily
from 15 Jan 2021 to 25 Dec 2023 (read off the page's dates-only movie at a dozen frames: linear).

    table   current   share of the frame drawn as bright white streamlines (strong, fast currents)
            motion    how much the frame changes from the previous one (flow and camera), 0..1
            swirl     motion inside the white streamlines only (the currents themselves moving)
            cur_x     horizontal centre of the white streamlines, 0 (left) .. 1 (right)
            cur_y     vertical centre, 0 (top) .. 1 (bottom)
            land      share of land colours (green / brown / snow)
            space     share of black space (1 - zoom: 0 when the camera is close)
    arrays  current   (frames, ROWS, COLS) white-streamline share per screen cell, 0..1 (x GRID_GAIN)

Picture indices: brightness and change of the rendered streamlines, not m/s.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import block_mean, frames, hsv

MOVIE = "perpetual_ocean2_CLOSE_093_clean_noDate_1080p30.mp4"
URL = "https://svs.gsfc.nasa.gov/vis/a000000/a005400/a005425/" + MOVIE
FPS = 30.0
SIZE = (480, 270)
ROWS, COLS = 9, 16
GRID_GAIN = 3.0
FIRST_DAY, LAST_DAY, LAST_FRAME = date(2021, 1, 15), date(2023, 12, 25), 9502
# from the measured zoom (space share) and the contact sheet of the movie
CHAPTERS = [("Turning globe", 0), ("Kuroshio", 2800), ("Indian Ocean and Agulhas", 3700),
            ("South Atlantic and Brazil", 5600), ("Gulf Stream", 6400), ("Gulf of Mexico", 8200),
            ("Back to the globe", 8900)]
NOTES = __doc__


def day_of(frame: int) -> date:
    return FIRST_DAY + timedelta(days=round((LAST_DAY - FIRST_DAY).days * min(frame, LAST_FRAME) / LAST_FRAME))


def labels(table: pd.DataFrame) -> list[str]:
    return [day_of(i).strftime("%d %b %Y") for i in range(len(table))]


def extract(path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    w, h = SIZE
    rows, grids, prev = [], [], None
    for _, bgr in frames(path, SIZE):
        hue, sat, val = hsv(bgr)
        white = (sat < 0.25) & (val > 0.72)
        land = (hue >= 25) & (hue < 110) & (sat > 0.2) & (val > 0.2)
        move = np.abs(val - prev) if prev is not None else np.zeros_like(val)
        total = white.sum()
        ys, xs = np.nonzero(white)
        rows.append(dict(current=white.mean(), motion=float(move.mean() * 4),
                         swirl=float(move[white].mean() * 4) if total else 0.0,
                         cur_x=float((xs.mean() + 0.5) / w) if total else 0.5,
                         cur_y=float((ys.mean() + 0.5) / h) if total else 0.5,
                         land=land.mean(), space=(val < 0.05).mean()))
        grids.append(np.clip(block_mean(white.astype(np.float32), ROWS, COLS) * GRID_GAIN, 0, 1))
        prev = val
    table = pd.DataFrame(rows)
    table[["motion", "swirl"]] = table[["motion", "swirl"]].clip(upper=1)
    return table, {"current": np.array(grids)}
