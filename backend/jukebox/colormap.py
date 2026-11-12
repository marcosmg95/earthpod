"""Colormap inversion: turn the colours of an SVS frame back into data values.

Pipeline: colorbar image -> lookup table (CIELAB colour -> position t in [0, 1]),
then every frame pixel -> nearest LUT colour; pixels farther than `max_de`
(land masks, coastlines, labels, compression noise) become NaN.
t is linear in the colorbar, so the correlation with GISTEMP doesn't depend on the
colorbar's degC range; a linear fit recovers that range as a bonus check.
Pure numpy + OpenCV (no scipy needed).
"""
from __future__ import annotations

import numpy as np
import cv2


def to_lab(rgb: np.ndarray) -> np.ndarray:
    """uint8 RGB (..., 3) -> float32 CIELAB (N, 3) with L in 0..100."""
    f = rgb.reshape(-1, 1, 3).astype(np.float32) / 255.0
    return cv2.cvtColor(f, cv2.COLOR_RGB2Lab).reshape(-1, 3)


def read_rgb(path) -> np.ndarray:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def lut_from_colorbar(rgb: np.ndarray, n: int = 256, flip: bool = False,
                      bg_tol: float = 10.0) -> tuple[np.ndarray, np.ndarray]:
    """Sample the colour ramp along the middle of a colorbar image.

    Horizontal bars run low->high left->right, vertical bars bottom->top
    (use flip=True if the bar is the other way round). Background is taken from
    the image corners; the ramp spans the first to last non-background pixel.
    """
    h, w = rgb.shape[:2]
    horizontal = w >= h
    line = rgb[h // 2, :, :] if horizontal else rgb[::-1, w // 2, :]
    lab = to_lab(line)
    corners = to_lab(np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]]))
    bg = np.median(corners, axis=0)
    fg = np.linalg.norm(lab - bg, axis=1) > bg_tol
    # ramp = first..last foreground pixel (not the longest run: diverging ramps pass
    # through near-white in the middle, which can match a white background)
    idx = np.flatnonzero(fg)
    if len(idx) < 10:
        raise ValueError("Could not find the colour ramp in the colorbar image")
    a, b = int(idx[0]), int(idx[-1]) + 1
    a, b = a + 2, b - 2  # avoid anti-aliased borders
    pos = np.linspace(a, b - 1, n).round().astype(int)
    lut_lab = lab[pos]
    t = np.linspace(0, 1, n)
    if flip:
        t = t[::-1]
    return lut_lab, t


def lut_from_matplotlib(name: str, n: int = 256) -> tuple[np.ndarray, np.ndarray]:
    """LUT from a named matplotlib colormap (handy for tests or known colormaps)."""
    import matplotlib
    cmap = matplotlib.colormaps[name]
    rgb = (np.array([cmap(x)[:3] for x in np.linspace(0, 1, n)]) * 255).astype(np.uint8)
    return to_lab(rgb), np.linspace(0, 1, n)


def invert(rgb: np.ndarray, lut_lab: np.ndarray, lut_t: np.ndarray,
           max_de: float = 12.0, chunk: int = 16384) -> np.ndarray:
    """Frame (H, W, 3) uint8 -> t (H, W) float with NaN where no colorbar colour matches."""
    h, w = rgb.shape[:2]
    px = to_lab(rgb)
    out = np.full(len(px), np.nan, dtype=np.float32)
    lut2 = (lut_lab ** 2).sum(1)
    for i in range(0, len(px), chunk):
        p = px[i:i + chunk]
        d2 = (p ** 2).sum(1)[:, None] - 2 * p @ lut_lab.T + lut2[None, :]
        j = d2.argmin(1)
        ok = d2[np.arange(len(p)), j] <= max_de ** 2
        out[i:i + chunk][ok] = lut_t[j[ok]]
    return out.reshape(h, w)


def area_mean(field: np.ndarray) -> float:
    """cos(latitude)-weighted mean of an equirectangular (lat x lon) field, NaN-aware."""
    h = field.shape[0]
    lat = np.deg2rad(90 - (np.arange(h) + 0.5) * 180 / h)
    wts = np.cos(lat)[:, None] * np.ones_like(field)
    m = ~np.isnan(field)
    return float((field[m] * wts[m]).sum() / wts[m].sum()) if m.any() else float("nan")


def coverage(field: np.ndarray) -> float:
    return float(np.mean(~np.isnan(field)))
