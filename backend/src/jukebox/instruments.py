"""Small additive instrument models shared by the ensemble sonification scripts.

Each model is a list of partials (ratio, amplitude, decay 1/s; 0 = held), attack / release (s),
ring = length of a struck note (s), vib = (rate Hz, depth), trem = (rate Hz, depth), breath = air noise level.
Struck instruments ring for their own `ring` whatever note length is asked for; sustained ones last `dur`.
Used by svs5196/co2_15 (regions of the CO2 movie) and svs5313/nightlights_grid_and_regions.
"""
import numpy as np

from . import mapping, synth

INSTRUMENTS = {
    "vibraphone": dict(struck=True, ring=2.6, attack=0.003, release=0.25, trem=(5.5, 0.30),
                       parts=[(1, 1.0, 0.9), (4, 0.30, 3.0), (10, 0.06, 9.0)]),
    "marimba":    dict(struck=True, ring=0.7, attack=0.002, release=0.05,
                       parts=[(1, 1.0, 5.0), (4, 0.35, 16.0), (9.9, 0.08, 40.0)]),
    "harp":       dict(struck=True, ring=1.8, attack=0.004, release=0.20,
                       parts=[(k, 1 / k ** 1.4, 1.2 + 0.9 * k) for k in range(1, 9)]),
    "kalimba":    dict(struck=True, ring=1.2, attack=0.002, release=0.10,
                       parts=[(1, 1.0, 2.8), (5.4, 0.22, 11.0), (13.1, 0.05, 28.0)]),
    "cello":      dict(struck=False, attack=0.18, release=0.35, vib=(5.0, 0.004),
                       parts=[(k, 1 / k ** 1.3 * (1.3 if k in (2, 3) else 1.0), 0) for k in range(1, 11)]),
    "flute":      dict(struck=False, attack=0.09, release=0.25, vib=(5.0, 0.003), breath=0.05,
                       parts=[(1, 1.0, 0), (2, 0.22, 0), (3, 0.08, 0)]),
    "oboe":       dict(struck=False, attack=0.05, release=0.18, vib=(5.5, 0.003),
                       parts=[(1, 0.45, 0), (2, 1.0, 0), (3, 0.80, 0), (4, 0.55, 0), (5, 0.35, 0),
                              (6, 0.20, 0), (7, 0.12, 0)]),
}


def is_struck(inst: str) -> bool:
    return INSTRUMENTS[inst]["struck"]


def tone(inst: str, freq: float, dur: float, sr: int = synth.SR) -> np.ndarray:
    """One note of an instrument model, mono, `dur` seconds (struck notes ring for their own `ring`)."""
    spec = INSTRUMENTS[inst]
    n = max(1, int((spec["ring"] if spec["struck"] else dur) * sr))
    t = np.arange(n) / sr
    rate, depth = spec.get("vib", (0.0, 0.0))
    phase = 2 * np.pi * freq * np.cumsum(1 + depth * np.sin(2 * np.pi * rate * t)) / sr
    y = sum(a * np.sin(k * phase) * (np.exp(-d * t) if d else 1.0)
            for k, a, d in spec["parts"] if freq * k < sr / 2)
    if spec.get("breath"):
        y = y + spec["breath"] * synth.band_noise(n, 1500, 5000, sr, seed=94)
    env = np.minimum(1.0, t / spec["attack"])
    rel = min(n, int(spec["release"] * sr))
    if rel:
        env[-rel:] *= np.linspace(1, 0, rel)
    if "trem" in spec:
        r, d = spec["trem"]
        env *= 1 - d * (0.5 - 0.5 * np.cos(2 * np.pi * r * t))
    return y * env


def scale_notes(low: int, range_semitones: int) -> list[int]:
    """MIDI notes of the shared D minor pentatonic (jukebox.mapping) from `low` to `low + range_semitones`."""
    return [m for m in range(low, low + range_semitones + 1) if (m - mapping.TONIC_MIDI) % 12 in mapping.SCALE]


def window(n: int, sr: int, t_in: float, t_out: float, fade: float) -> np.ndarray:
    """0..1 per sample: smooth fade in after t_in, fade out before t_out (each `fade` seconds)."""
    t = np.arange(n) / sr
    up = np.clip((t - t_in) / fade, 0, 1)
    down = np.clip((t_out - t) / fade, 0, 1)
    e = np.minimum(up, down)
    return e * e * (3 - 2 * e)


def ranks(values) -> np.ndarray:
    """Each value's place among all of them, 0 (lowest) .. 1 (highest); 0.5 for all if they are equal.

    A rank scale keeps one bright spike from squashing the rest of a melody onto a single pitch.
    """
    raw = np.asarray(values, dtype=float)
    if raw.size < 2 or np.ptp(raw) <= 1e-9:
        return np.full(raw.size, 0.5)
    return np.argsort(np.argsort(raw, kind="stable"), kind="stable") / (len(raw) - 1)
