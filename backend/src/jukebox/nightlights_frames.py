"""Screen-space light features from NASA SVS 5313's 2160p EIC movie.

These are picture indices, not calibrated radiance. Zooms, map details and overlays
can affect them; the central year label and colour legend are masked out.

The movie (1300 frames, 30 fps, Earth shown twice side by side) has four scenes, found by
looking at its frames (year-label changes measured to the frame):

    frames    0-288   global map, 2012 -> 2023 (one year every ~18 frames from frame 15)
    frames  289-630   global change map: purple = "new lights", orange = "lights out" (SVS legend)
    frames  631-1103  four zoom boxes fade in (frames 668-690), then 2012 -> 2023 again from frame 830
    frames 1104-1299  the same boxes and map as a change map

Per frame we measure the bright-pixel level of the whole picture (`light`, `x`), the part of it
coloured purple or orange (`purple`, `orange`), and the same three values inside each zoom box
(`weur_light`, `weur_purple`, ...). Before frame 668 the box rectangles show the plain map.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .data import DERIVED_DIR

MOVIE = "nightlights_flat_series_and_change_wZooms_13_EIC_2160p30_h265.mp4"
FPS = 30.0
FRAME_COUNT = 1300
SIZE = (960, 270)
FEATURES_PATH = DERIVED_DIR / "svs5313_eic_frames.csv"

LEGEND_MASK = (0.43, 0.43, 0.58, 0.68)  # x0, y0, x1, y1 (fractions): year label + colour legend
V_MIN = 65                              # 0..255; darker pixels (land shading, ocean) count as 0
PURPLE_HUE, PURPLE_SAT = (115, 170), 40  # OpenCV hue 0..179: legend "new lights" ~ 125-150
ORANGE_HUE, ORANGE_SAT = (0, 18), 60     # legend "lights out" ~ 10-16; gold year lights are 20-28


@dataclass(frozen=True)
class Box:
    key: str
    name: str
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1 as fractions, inside the box border

    @property
    def pan(self) -> float:
        """Screen position of the box centre, -1 (left) .. +1 (right)."""
        return round((self.rect[0] + self.rect[2]) - 1, 3)


BOXES = (
    Box("weur", "Western Europe", (0.095, 0.40, 0.255, 0.94)),
    Box("emed", "Eastern Mediterranean", (0.313, 0.11, 0.416, 0.575)),
    Box("ukr", "Ukraine", (0.610, 0.09, 0.742, 0.415)),
    Box("ind", "India", (0.793, 0.54, 0.918, 0.96)),
)
BOXES_IN = (668, 690)  # frames over which the zoom boxes fade in

# (first frame, key, description); a scene lasts until the next one starts
SCENES = (
    (0, "years", "global map"),
    (289, "change", "global change map"),
    (631, "zoom_years", "regional zooms"),
    (1104, "zoom_change", "regional zooms, change map"),
)
# frame at which each year 2012..2023 appears, in the two year-by-year scenes
YEAR_FRAMES = {
    "years": (0, 15, 33, 51, 69, 86, 104, 122, 139, 157, 175, 193),
    "zoom_years": (631, 830, 848, 866, 884, 901, 919, 937, 954, 972, 990, 1008),
}
FIRST_YEAR = 2012
# chapters for the player: (title, first frame)
SECTIONS = (
    ("1 · Years 2012–2023", 0),
    ("2 · Change map", 289),
    ("3 · Regional zooms", 631),
)

COLUMNS = ["light", "x", "purple", "orange"] + [
    f"{b.key}_{kind}" for b in BOXES for kind in ("light", "purple", "orange")]


def scene_of(frames) -> np.ndarray:
    """Scene key for each (possibly fractional) frame index."""
    starts = np.array([s[0] for s in SCENES])
    keys = np.array([s[1] for s in SCENES])
    return keys[np.searchsorted(starts, np.asarray(frames), side="right") - 1]


def labels() -> list[str]:
    """One label per frame: what is on screen ('2015 · global map', 'Change 2012–2023 · ...')."""
    out = []
    for i, key in enumerate(scene_of(np.arange(FRAME_COUNT))):
        where = dict((k, d) for _, k, d in SCENES)[key]
        if key in YEAR_FRAMES:
            year = FIRST_YEAR + int(np.searchsorted(YEAR_FRAMES[key], i, side="right")) - 1
            out.append(f"{year} · {where}")
        else:
            out.append(f"Change 2012–2023 · {where.replace(', change map', '')}")
    return out


# ---- coarse spatial grids (what the three-acts sonification scans) --------------------------
# One copy of the world map (the movie shows two side by side; the year label sits in the gap),
# and the inside of each zoom box. Rows run north -> south, columns west -> east.
GRIDS_PATH = DERIVED_DIR / "svs5313_eic_grids.npz"
WORLD_RECT = (0.0, 0.06, 0.5625, 0.80)
WORLD_GRID = (15, 64)   # rows, columns
BOX_GRID = (15, 20)
GRID_MASK = (0.48, 0.47, 0.58, 0.64)  # year label + legend, in the gap between the two maps
GRID_KEYS = ("world_light", "world_purple", "world_orange", "box_light", "box_purple", "box_orange")
# frames measured: mid-way through each year, and a settled frame of each change map
CHANGE_FRAME, ZOOM_CHANGE_FRAME = 450, 1250


def year_windows(scene: str) -> list[tuple[int, int]]:
    """(first, last+1) frame of each year 2012..2023 in a year-by-year scene."""
    starts = YEAR_FRAMES[scene]
    next_scene = SCENES[[s[1] for s in SCENES].index(scene) + 1][0]
    return list(zip(starts, list(starts[1:]) + [next_scene]))


def _grid_layers(bgr: np.ndarray):
    import cv2

    small = cv2.resize(bgr, (1920, 540), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hue, sat = hsv[:, :, 0], hsv[:, :, 1]
    value = hsv[:, :, 2].astype(float) / 255
    value[value <= V_MIN / 255] = 0
    _region(value, GRID_MASK)[:] = 0
    purple = value * ((hue >= PURPLE_HUE[0]) & (hue <= PURPLE_HUE[1]) & (sat >= PURPLE_SAT))
    orange = value * ((hue >= ORANGE_HUE[0]) & (hue <= ORANGE_HUE[1]) & (sat >= ORANGE_SAT))
    return value, purple, orange


def _grid(layer: np.ndarray, rect, shape) -> np.ndarray:
    import cv2

    return cv2.resize(_region(layer, rect), (shape[1], shape[0]), interpolation=cv2.INTER_AREA)


def extract_grids(movie: str | Path) -> dict[str, np.ndarray]:
    """World and zoom-box light grids at the frames listed above (see GRID_KEYS)."""
    import cv2

    windows = {s: year_windows(s) for s in YEAR_FRAMES}
    wanted = {(a + b) // 2: (s, i) for s, w in windows.items() for i, (a, b) in enumerate(w)}
    wanted[CHANGE_FRAME], wanted[ZOOM_CHANGE_FRAME] = ("change", 0), ("zoom_change", 0)
    n_years = len(YEAR_FRAMES["years"])
    out = {"world_light": np.zeros((n_years, *WORLD_GRID)), "world_purple": np.zeros(WORLD_GRID),
           "world_orange": np.zeros(WORLD_GRID), "box_light": np.zeros((len(BOXES), n_years, *BOX_GRID)),
           "box_purple": np.zeros((len(BOXES), *BOX_GRID)), "box_orange": np.zeros((len(BOXES), *BOX_GRID))}
    cap = cv2.VideoCapture(str(movie))
    if not cap.isOpened():
        raise OSError(f"Could not open movie: {movie}")
    try:
        for index in range(max(wanted) + 1):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Movie ended at frame {index}")
            if index not in wanted:
                continue
            scene, year = wanted[index]
            value, purple, orange = _grid_layers(frame)
            if scene == "years":
                out["world_light"][year] = _grid(value, WORLD_RECT, WORLD_GRID)
            elif scene == "change":
                out["world_purple"][:] = _grid(purple, WORLD_RECT, WORLD_GRID)
                out["world_orange"][:] = _grid(orange, WORLD_RECT, WORLD_GRID)
            elif scene == "zoom_years":
                for k, b in enumerate(BOXES):
                    out["box_light"][k, year] = _grid(value, b.rect, BOX_GRID)
            else:
                for k, b in enumerate(BOXES):
                    out["box_purple"][k] = _grid(purple, b.rect, BOX_GRID)
                    out["box_orange"][k] = _grid(orange, b.rect, BOX_GRID)
    finally:
        cap.release()
    return {k: v.astype(np.float32).round(6) for k, v in out.items()}


def load_grids(viz_id: int, movie: str) -> dict[str, np.ndarray] | None:
    if viz_id != 5313 or movie != MOVIE or not GRIDS_PATH.exists():
        return None
    with np.load(GRIDS_PATH) as z:
        missing = [k for k in GRID_KEYS if k not in z]
        if missing:
            raise ValueError(f"{GRIDS_PATH.name} lacks {missing}: re-run scripts/poc7_svs5313_features.py")
        return {k: z[k].astype(float) for k in GRID_KEYS}


@dataclass
class NightLightsFeatures:
    table: pd.DataFrame

    def resampled(self, column: str, n: int, sr: int) -> np.ndarray:
        values = self.table[column].to_numpy(float)
        return np.interp(np.arange(n) * FPS / sr, np.arange(len(values)), values)


def frame_envelope(per_frame: np.ndarray, n: int, sr: int, smooth: int = 9) -> np.ndarray:
    """A per-frame 0..1 gain, smoothed over `smooth` frames (no clicks) and stretched to n samples."""
    per_frame = np.asarray(per_frame, dtype=float)
    if smooth > 1:
        kernel = np.hanning(smooth + 2)[1:-1]
        padded = np.pad(per_frame, smooth, mode="edge")
        per_frame = np.convolve(padded, kernel / kernel.sum(), mode="same")[smooth:-smooth]
    return np.interp(np.arange(n) * FPS / sr, np.arange(len(per_frame)), per_frame)


def scene_envelope(keys, n: int, sr: int, frame_count: int = FRAME_COUNT, smooth: int = 9) -> np.ndarray:
    """1 while one of the scenes in `keys` is on screen, 0 otherwise, with smoothed edges."""
    return frame_envelope(np.isin(scene_of(np.arange(frame_count)), list(keys)).astype(float), n, sr, smooth)


def boxes_envelope(n: int, sr: int, frame_count: int = FRAME_COUNT) -> np.ndarray:
    """0 before the zoom boxes appear, ramping to 1 while they fade in."""
    ramp = np.clip((np.arange(frame_count) - BOXES_IN[0]) / (BOXES_IN[1] - BOXES_IN[0]), 0, 1)
    return frame_envelope(ramp, n, sr, smooth=1)


def year_change_frames() -> list[tuple[int, str, int]]:
    """(frame, scene, year) for every frame where a new year label appears (2013..2023)."""
    return [(f, key, FIRST_YEAR + i) for key, frames in YEAR_FRAMES.items()
            for i, f in enumerate(frames) if i > 0]


def _region(a: np.ndarray, rect) -> np.ndarray:
    h, w = a.shape[:2]
    x0, y0, x1, y1 = rect
    return a[int(h * y0):int(h * y1), int(w * x0):int(w * x1)]


def measure(bgr: np.ndarray) -> dict[str, float]:
    """Bright-pixel level, its horizontal centroid (0..1), and its purple/orange parts, overall and per box."""
    import cv2

    small = cv2.resize(bgr, SIZE, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hue, sat = hsv[:, :, 0], hsv[:, :, 1]
    value = hsv[:, :, 2].astype(float) / 255
    value[value <= V_MIN / 255] = 0
    _region(value, LEGEND_MASK)[:] = 0
    purple = value * ((hue >= PURPLE_HUE[0]) & (hue <= PURPLE_HUE[1]) & (sat >= PURPLE_SAT))
    orange = value * ((hue >= ORANGE_HUE[0]) & (hue <= ORANGE_HUE[1]) & (sat >= ORANGE_SAT))

    total = value.sum()
    x = float((value.sum(axis=0) * np.linspace(0, 1, value.shape[1])).sum() / total) if total else 0.5
    out = {"light": float(value.mean()), "x": x, "purple": float(purple.mean()), "orange": float(orange.mean())}
    for b in BOXES:
        for kind, layer in (("light", value), ("purple", purple), ("orange", orange)):
            out[f"{b.key}_{kind}"] = float(_region(layer, b.rect).mean())
    return out


def extract(movie: str | Path) -> pd.DataFrame:
    """Measure the specific SVS 5313 movie, checking its frame rate and length."""
    import cv2

    cap = cv2.VideoCapture(str(movie))
    if not cap.isOpened():
        raise OSError(f"Could not open movie: {movie}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not np.isclose(fps, FPS, atol=0.01):
            raise ValueError(f"Expected {FPS:g} fps, got {fps:g}")
        rows = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rows.append({"frame": len(rows), **measure(frame)})
        if len(rows) != FRAME_COUNT:
            raise ValueError(f"Expected {FRAME_COUNT} frames, decoded {len(rows)}")
        return pd.DataFrame(rows, columns=["frame"] + COLUMNS).round(6)
    finally:
        cap.release()


def load(viz_id: int, movie: str) -> NightLightsFeatures | None:
    if viz_id != 5313 or movie != MOVIE or not FEATURES_PATH.exists():
        return None
    table = pd.read_csv(FEATURES_PATH)
    if len(table) != FRAME_COUNT or not np.array_equal(table.frame.to_numpy(), np.arange(FRAME_COUNT)):
        raise ValueError(f"Invalid frame sequence in {FEATURES_PATH}")
    missing = [c for c in COLUMNS if c not in table]
    if missing:
        raise ValueError(f"{FEATURES_PATH.name} lacks {missing}: re-run scripts/poc7_svs5313_features.py")
    return NightLightsFeatures(table)
