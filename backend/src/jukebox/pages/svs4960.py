"""SVS 4960 — A 3D view of an atmospheric river (GEOS / MERRA-2 style model run), Oct–Dec 2010. 4 min 52 s.

The camera starts on a cloudy globe, dives to the northeast Pacific where a band of moisture (translucent
blue: water vapour transport) streams toward California, follows it over the Sierra Nevada (orographic lift,
rain in yellow / orange / red), and pulls back to the globe. Model time does not run steadily: it jumps and
replays (1 Oct -> 7 Dec in the first 27 s, then around 3-13 Dec), so every frame's date is read from the
page's dates-only movie (atmos_river_DATE_ONLY_HD.mp4) with glyph templates (data/derived/svs4960_glyphs.npz).

    table   moisture  share of the frame drawn in the moisture blue, weighted by its strength (0..1)
            moist_x   horizontal centre of the moisture, 0 (left) .. 1 (right)
            rain      share of the frame in rain colours (yellow / orange / red / magenta)
            cloud     share of white / grey cloud (mostly the opening globe)
            land      share of terrain colours (green / brown / snow)
            space     share of black space around the globe (1 - zoom)
            motion    mean brightness change from the previous frame (camera and flow speed)
            day       model time in days since 1 Oct 2010 00:00 (from the date movie), -1 if unread
    arrays  moisture  (frames, ROWS, COLS) moisture strength per screen cell

Picture indices: colours of the rendered scene, not kg/m/s or mm/h.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import block_mean, frames, hsv, raw_path
from ..paths import DERIVED_DIR

MOVIE = "atmos_river_HD.mp4"
URL = "https://svs.gsfc.nasa.gov/vis/a000000/a004900/a004960/" + MOVIE
DATES_MOVIE = "atmos_river_DATE_ONLY_HD.mp4"
DATES_URL = "https://svs.gsfc.nasa.gov/vis/a000000/a004900/a004960/" + DATES_MOVIE
EXTRA = {DATES_MOVIE: DATES_URL}       # other files extract() needs, downloaded next to MOVIE
FPS = 59.94005994005994
SIZE = (960, 540)                      # small rain blobs vanish at lower resolutions
ROWS, COLS = 9, 16
T0 = datetime(2010, 10, 1)
GLYPHS = DERIVED_DIR / "svs4960_glyphs.npz"
TEXT = (498, 584, 330, 1540)           # y0, y1, x0, x1 of the date line in the 1080p dates movie
MONTHS = {"O": 10, "N": 11, "D": 12}
# from the measured scene changes: clouds vanish (~1670), close-up (2090), California coast in view (~9000),
# terrain fills the screen (10170-11640), camera pulls out (14900)
CHAPTERS = [("Cloudy globe", 0), ("The river over the Pacific", 1670), ("Landfall in California", 9000),
            ("Over the Sierra Nevada", 10170), ("The storm moves on", 11640), ("Back to the globe", 14900)]
NOTES = __doc__


# ---- reading the dates movie ------------------------------------------------------------------------------

def _templates():
    with np.load(GLYPHS) as z:
        return z["glyphs"].astype(float) / 255, [str(n) for n in z["names"]]


def _glyphs(gray: np.ndarray) -> list[np.ndarray]:
    import cv2

    y0, y1, x0, x1 = TEXT
    line = gray[y0:y1, x0:x1] > 110
    cols = line.any(axis=0)
    out, x = [], 0
    while x < len(cols):
        if not cols[x]:
            x += 1
            continue
        b = x
        while b < len(cols) and cols[b]:
            b += 1
        g = line[:, x:b]
        rows = np.flatnonzero(g.any(axis=1))
        out.append(cv2.resize(g[rows[0]:rows[-1] + 1].astype(np.uint8) * 255, (16, 24),
                              interpolation=cv2.INTER_AREA).astype(float) / 255)
        x = b
    return out


def read_date(gray: np.ndarray, templates=None) -> float:
    """Days since T0 printed on one frame of the dates movie, or -1 if it cannot be read."""
    reps, names = templates or _templates()
    chars = []
    for g in _glyphs(gray):
        d = np.abs(reps - g).mean(axis=(1, 2))
        chars.append(names[int(d.argmin())])
    if not chars or chars[0] not in MONTHS:
        return -1.0
    digits = "".join("0" if c in "Oo" else c for c in chars[3:] if c.isdigit() or c in "Oo")
    if len(digits) != 10:
        return -1.0
    day, year, hour, minute = int(digits[:2]), int(digits[2:6]), int(digits[6:8]), int(digits[8:])
    try:
        t = datetime(year, MONTHS[chars[0]], day, hour, minute)
    except ValueError:
        return -1.0
    return (t - T0).total_seconds() / 86400


def read_dates(path) -> np.ndarray:
    import cv2

    templates, out = _templates(), []
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        out.append(read_date(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), templates))
    cap.release()
    days = np.array(out)
    bad = days < 0                            # fill the few unreadable frames from their neighbours
    if bad.any() and (~bad).any():
        days[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), days[~bad])
    return days


def labels(table: pd.DataFrame) -> list[str]:
    return [(T0 + timedelta(days=float(d))).strftime("%d %b %Y %Hh") if d >= 0 else "—" for d in table.day]


# ---- measuring the movie ----------------------------------------------------------------------------------

def layers(bgr: np.ndarray) -> dict[str, np.ndarray]:
    hue, sat, val = hsv(bgr)
    moisture = ((hue >= 180) & (hue < 225) & (sat > 0.35) & (val > 0.45)) * np.clip((sat - 0.35) / 0.5, 0, 1) * val
    # rain blobs: saturated yellow -> red (terrain shares the yellow hues but stays below ~0.6 saturation);
    # the yellow annotation text ("atmospheric river", "orographic lift") also counts, for a few seconds
    rain = (((hue <= 64) & (sat > 0.68)) | (((hue < 25) | (hue >= 300)) & (sat > 0.5))) & (val > 0.45)
    cloud = (sat < 0.15) & (val > 0.55)
    land = (hue >= 45) & (hue < 110) & (sat > 0.25) & (val > 0.25)
    space = val < 0.06
    return {"moisture": moisture, "rain": rain, "cloud": cloud, "land": land, "space": space}


def extract(path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    import cv2

    dates_path = raw_path(4960).with_name(DATES_MOVIE)
    if not dates_path.exists():
        raise FileNotFoundError(f"{dates_path} is missing: python -m jukebox.measure 4960 downloads it (EXTRA)")
    days = read_dates(dates_path)
    w = SIZE[0]
    rows, grids, prev = [], [], None
    for i, bgr in frames(path, SIZE):
        L = layers(bgr)
        m = L["moisture"]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        total = m.sum()
        rows.append(dict(moisture=m.mean(),
                         moist_x=float((m.sum(axis=0) * (np.arange(w) + 0.5) / w).sum() / total) if total else 0.5,
                         rain=L["rain"].mean(), cloud=L["cloud"].mean(), land=L["land"].mean(),
                         space=L["space"].mean(),
                         motion=float(np.abs(gray - prev).mean()) if prev is not None else 0.0,
                         day=float(days[min(i, len(days) - 1)]) if len(days) else -1.0))
        grids.append(np.clip(block_mean(m, ROWS, COLS) * 2, 0, 1))
        prev = gray
    return pd.DataFrame(rows), {"moisture": np.array(grids)}
