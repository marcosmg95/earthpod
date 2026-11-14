"""Per-frame colour features measured from an SVS movie (first use: SVS 5196, DYAMOND global CO2).

The movie has no numeric colour scale and its colour bar is semi-transparent, so these are
*indices of the picture*, not ppm: how much of each frame is drawn in the orange-red end of the
colour bar (the densest CO2) and where on screen it is. One row per movie frame.

    plume      % of the frame that is orange-red (dense CO2)
    haze       % of the frame that is tan (medium CO2 over a dark background)
    x, y       centre of the orange-red area, 0..1 from left / top (0.5 when there is none)
    top/mid/bottom   plume in the upper / middle / lower third of the frame
    label      date-time printed on the frame when known ("14 Jan 2020 22:00"), else "frame 0001"

`profiles` (frames x PROFILE_COLS, uint8) is the orange-red amount in each screen column,
left to right: the raw material for audification and model-based scripts.
Built by scripts/poc6_svs5196_features.py; the results are committed in data/derived/.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .data import DERIVED_DIR

ANALYSIS_SIZE = (480, 270)      # width, height
PROFILE_COLS = 120             # must divide the analysis width
STAMP = (0.78, 0.92)            # the date stamp sits right of / below these fractions: ignored

# SVS 5196 movies: tag -> (text found in the filename, date-time of frame 0 or None, hours per frame).
# The orbit movie prints its date on every frame: frame 0 = 14 Jan 2020 22:00 and frame 1174 =
# 03 Mar 2020 20:00, so one frame is one hour of model time. The other camera moves print no date.
SVS5196_MOVIES = {
    "orbit": ("globe_orbit", datetime(2020, 1, 14, 22), 1.0),
    "zoomwest": ("globe_zoomwest", None, None),
    "zoom": ("globe_zoom_", None, None),       # eastern United States (16:9 versions)
    "tilt": ("globe_tilt", None, None),
}


def movie_tag(filename: str) -> str | None:
    """Which SVS 5196 camera move a movie file is ('orbit', 'zoom', ...), or None."""
    if "5x3" in filename:           # 5x3 wall version: a different crop, not measured
        return None
    for tag, (needle, _, _) in SVS5196_MOVIES.items():
        if needle in filename:
            return tag
    return None


@dataclass
class FrameFeatures:
    tag: str
    table: pd.DataFrame          # one row per frame (see module docstring)
    profiles: np.ndarray         # (frames, PROFILE_COLS) float 0..1

    @property
    def dated(self) -> bool:
        return not self.table.label.iloc[0].startswith("frame")

    @property
    def times(self) -> list[datetime] | None:
        return [datetime.strptime(x, "%d %b %Y %H:%M") for x in self.table.label] if self.dated else None

    def resampled(self, column: str, n: int) -> np.ndarray:
        """A column stretched to n values (linear), e.g. one per audio sample."""
        v = self.table[column].to_numpy(float)
        return np.interp(np.linspace(0, len(v) - 1, n), np.arange(len(v)), v)


def labels_for(tag: str, n: int) -> list[str]:
    _, start, hours = SVS5196_MOVIES[tag]
    if start is None:
        return [f"frame {i + 1:04d}" for i in range(n)]
    return [(start + timedelta(hours=hours * i)).strftime("%d %b %Y %H:%M") for i in range(n)]


def extract(movie_path: str | Path, tag: str) -> tuple[pd.DataFrame, np.ndarray]:
    """Measure every frame of a movie -> (table, uint8 profiles). Needs OpenCV."""
    import cv2

    cap = cv2.VideoCapture(str(movie_path))
    w, h = ANALYSIS_SIZE
    keep = np.ones((h, w), bool)
    keep[int(STAMP[1] * h):, int(STAMP[0] * w):] = False
    thirds = [slice(0, h // 3), slice(h // 3, 2 * h // 3), slice(2 * h // 3, h)]
    xs, ys = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    rows, profiles = [], []
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        small = cv2.resize(bgr, ANALYSIS_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        hue, sat, val = cv2.split(cv2.cvtColor(small, cv2.COLOR_BGR2HSV))     # hue in degrees
        hot = ((hue < 32) & (sat > 0.6) & (val > 0.45) & keep).astype(np.float32)
        tan = ((hue >= 25) & (hue < 55) & (sat > 0.3) & (val > 0.12) & (val <= 0.6) & keep)
        total = float(hot.sum())
        rows.append(dict(
            plume=100 * hot.mean(), haze=100 * tan.mean(),
            x=float((hot * xs).sum() / total) if total else 0.5,
            y=float((hot * ys).sum() / total) if total else 0.5,
            top=100 * hot[thirds[0]].mean(), mid=100 * hot[thirds[1]].mean(),
            bottom=100 * hot[thirds[2]].mean(),
        ))
        col = hot.mean(axis=0).reshape(PROFILE_COLS, -1).mean(axis=1)         # share of each column
        profiles.append(col)
    cap.release()
    table = pd.DataFrame(rows).round(4)
    table.insert(0, "frame", range(len(table)))
    table.insert(1, "label", labels_for(tag, len(table)))
    prof = np.array(profiles)
    return table, np.round(np.clip(prof / max(prof.max(), 1e-9), 0, 1) * 255).astype(np.uint8)


def path_for(viz_id: int, tag: str) -> Path:
    return DERIVED_DIR / f"svs{viz_id}_{tag}_frames.csv"


def load(viz_id: int, movie_filename: str) -> FrameFeatures | None:
    """Committed features for one movie of an SVS page (None if that movie was not measured)."""
    tag = movie_tag(movie_filename) if viz_id == 5196 else None
    if tag is None or not path_for(viz_id, tag).exists():
        return None
    table = pd.read_csv(path_for(viz_id, tag))
    with np.load(DERIVED_DIR / f"svs{viz_id}_profiles.npz") as z:
        profiles = z[tag].astype(float) / 255
    return FrameFeatures(tag, table, profiles)
