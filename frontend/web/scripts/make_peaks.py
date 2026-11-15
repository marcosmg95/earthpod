#!/usr/bin/env python3
"""Write <name>.peaks.json next to every .wav in public/data, so the sound chart appears instantly.

    python scripts/make_peaks.py            # all files that have no .peaks.json yet
    python scripts/make_peaks.py --force    # redo them all

Needs ffmpeg and numpy. Same maths as analyse() in src/engine/waveform.ts.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

BINS = 480
SR = 44100  # the browser decodes at this rate in analyse()

p = argparse.ArgumentParser()
p.add_argument("--force", action="store_true")
a = p.parse_args()


def normalise(x: np.ndarray, q: float) -> np.ndarray:
    s = np.sort(x)
    top = max(1e-6, float(s[min(len(s) - 1, int(q * len(s)))]))
    return np.minimum(1.0, x / top)


def peaks(path: Path) -> dict:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = len(x)
    per = max(1, n // BINS)
    level = np.zeros(BINS)
    bright = np.zeros(BINS)
    for b in range(BINS):
        seg = x[b * per : min(n, b * per + per)]
        if len(seg) == 0:
            continue
        pos = seg >= 0
        prev = np.concatenate(([True], pos[:-1]))
        level[b] = np.sqrt(np.mean(seg.astype(np.float64) ** 2))
        bright[b] = np.count_nonzero(pos != prev) / len(seg)
    return {
        "duration": round(n / SR, 3),
        "level": [round(v, 4) for v in normalise(level, 1).tolist()],
        "bright": [round(v, 4) for v in normalise(bright, 0.95).tolist()],
    }


root = Path(__file__).resolve().parent.parent / "public" / "data"
for wav in sorted(root.rglob("*.wav")):
    out = wav.with_suffix(".peaks.json")
    if out.exists() and not a.force:
        continue
    out.write_text(json.dumps(peaks(wav), separators=(",", ":")))
    print("wrote", out.relative_to(root))