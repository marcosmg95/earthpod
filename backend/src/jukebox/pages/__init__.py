"""Frame measurements for the challenge's SVS pages: one module per page (svs<id>.py), one shared format.

Each page module measures one movie (or one still image) of its SVS page and says how to label its frames:

    MOVIE    filename of the measured movie / image on the SVS page (what the explorer's selector shows)
    URL      where to download it (scripts/poc8_page_features.py puts it in data/raw/svs<id>/)
    FPS      the movie's frame rate; for a still image, scan steps per second (see STILL)
    STILL    True for a still image: the "movie" is a left-to-right scan of it, one table row per step,
             and the explorer shows the image with a moving scan line instead of a video
    CHAPTERS [(title, frame)] sections for the player's chapter buttons (optional)
    NOTES    one paragraph: what the columns mean and what they are not (picture indices, not physical units)
    def extract(path) -> (table, arrays)     table: one row per frame (no frame/label columns),
                                              arrays: name -> np.ndarray with frames first
    def labels(table) -> list[str]           one label per frame of the measured table (dates, longitudes, ...)

scripts/poc8_page_features.py runs extract() and writes data/derived/svs<id>_frames.csv + svs<id>_arrays.npz
(committed, small), which load() reads back for the sonification scripts (ctx.page_features()).
All measurements are indices of the picture (colour share, brightness, screen position), not physical values.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd

from ..data import DERIVED_DIR, RAW_DIR

PAGES = (5669, 5533, 4950, 5011, 3912, 5425, 4960)   # the challenge's Resources tab, besides 5196 / 5313


def module(viz_id: int) -> ModuleType | None:
    """The measuring module of an SVS page, or None if this project has none."""
    if int(viz_id) not in PAGES:
        return None
    return importlib.import_module(f"{__name__}.svs{int(viz_id)}")


def spec_for(viz_id: int, filename: str) -> ModuleType | None:
    """The page module if `filename` is the movie / image it measures."""
    mod = module(viz_id)
    return mod if mod is not None and mod.MOVIE == filename else None


def table_path(viz_id: int) -> Path:
    return DERIVED_DIR / f"svs{viz_id}_frames.csv"


def arrays_path(viz_id: int) -> Path:
    return DERIVED_DIR / f"svs{viz_id}_arrays.npz"


def raw_path(viz_id: int) -> Path:
    return RAW_DIR / f"svs{viz_id}" / module(viz_id).MOVIE


@dataclass
class PageFeatures:
    viz_id: int
    movie: str
    fps: float
    still: bool
    table: pd.DataFrame          # frame, label, then the page's columns
    arrays: dict[str, np.ndarray]
    chapters: list[tuple[str, int]]

    @property
    def labels(self) -> list[str]:
        return self.table.label.astype(str).tolist()

    @property
    def n_frames(self) -> int:
        return len(self.table)

    @property
    def duration(self) -> float:
        return self.n_frames / self.fps

    def per_sample(self, per_frame, n: int, sr: int, smooth: int = 1) -> np.ndarray:
        """A per-frame series stretched to n audio samples (frame i covers i/fps .. (i+1)/fps).

        smooth > 1 first averages it over that many frames (Hann window): no clicks from frame steps.
        """
        v = np.asarray(per_frame, dtype=float)
        if smooth > 1:
            k = np.hanning(smooth + 2)[1:-1]
            v = np.convolve(np.pad(v, smooth, mode="edge"), k / k.sum(), mode="same")[smooth:-smooth]
        return np.interp(np.arange(n) * self.fps / sr - 0.5, np.arange(len(v)), v)

    def column(self, name: str, n: int, sr: int, smooth: int = 1) -> np.ndarray:
        return self.per_sample(self.table[name].to_numpy(float), n, sr, smooth)

    def chapter_times(self) -> list[tuple[str, float]]:
        return [(title, frame / self.fps) for title, frame in self.chapters]


def load(viz_id: int, filename: str) -> PageFeatures | None:
    """Committed measurements of one movie / image of an SVS page (None if it was not measured)."""
    mod = spec_for(viz_id, filename)
    if mod is None or not table_path(viz_id).exists():
        return None
    table = pd.read_csv(table_path(viz_id), keep_default_na=False)
    arrays = {}
    if arrays_path(viz_id).exists():
        with np.load(arrays_path(viz_id)) as z:
            arrays = {k: z[k].astype(float) / (255.0 if z[k].dtype == np.uint8 else 1.0) for k in z.files}
    return PageFeatures(int(viz_id), filename, float(mod.FPS), bool(getattr(mod, "STILL", False)), table, arrays,
                        list(getattr(mod, "CHAPTERS", [])))


def save(viz_id: int, table: pd.DataFrame, arrays: dict[str, np.ndarray]) -> None:
    """Write a page's measurements: arrays in 0..1 are stored as uint8 (1/255 steps) to keep the files small."""
    mod = module(viz_id)
    table = table.round(4)
    table.insert(0, "frame", range(len(table)))
    table.insert(1, "label", mod.labels(table))
    table.to_csv(table_path(viz_id), index=False, lineterminator="\n")
    packed = {}
    for k, a in arrays.items():
        a = np.asarray(a, dtype=float)
        if len(a) != len(table):
            raise ValueError(f"array {k!r} has {len(a)} rows, the table {len(table)}")
        packed[k] = np.round(np.clip(a, 0, 1) * 255).astype(np.uint8) if a.min() >= 0 and a.max() <= 1 \
            else a.astype(np.float32)
    np.savez_compressed(arrays_path(viz_id), **packed)


# ---- helpers shared by the page modules -------------------------------------------------------------------

def frames(path: str | Path, size: tuple[int, int], every: int = 1):
    """(index, BGR frame resized to `size` = (w, h)) for every `every`-th frame of a movie. Needs OpenCV."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise OSError(f"Could not open movie: {path}")
    i = 0
    try:
        while True:
            ok = cap.grab()
            if not ok:
                break
            if i % every == 0:
                ok, bgr = cap.retrieve()
                if not ok:
                    break
                yield i, cv2.resize(bgr, size, interpolation=cv2.INTER_AREA)
            i += 1
    finally:
        cap.release()


def hsv(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hue in degrees 0..360, saturation and value 0..1."""
    import cv2

    h = cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2HSV)
    return h[:, :, 0], h[:, :, 1], h[:, :, 2]


def lightness(bgr: np.ndarray) -> np.ndarray:
    """CIELAB L* 0..100."""
    import cv2

    return cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)[:, :, 0]


def block_mean(a: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Mean of a 2-D array over a rows x cols grid of blocks (the array is cropped to fit)."""
    h, w = a.shape[:2]
    a = a[: h - h % rows, : w - w % cols]
    return a.reshape(rows, a.shape[0] // rows, cols, a.shape[1] // cols).mean(axis=(1, 3))


def centroid(weights: np.ndarray, axis: int) -> float:
    """Weighted mean position 0..1 along an axis of a 2-D array (0.5 if the weights are all zero)."""
    total = float(weights.sum())
    if total <= 0:
        return 0.5
    pos = (np.arange(weights.shape[axis]) + 0.5) / weights.shape[axis]
    return float((weights.sum(axis=1 - axis) * pos).sum() / total)


def lon_label(lon: float, step: int = 5) -> str:
    """-122.3 -> '120°W' (rounded to `step` degrees)."""
    v = int(round(((lon + 180) % 360 - 180) / step) * step)
    if v in (180, -180):
        return "180°"
    return "0°" if v == 0 else f"{abs(v)}°{'E' if v > 0 else 'W'}"
