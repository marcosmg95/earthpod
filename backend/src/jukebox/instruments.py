"""Small instrument models shared by the ensemble sonification scripts.

Acoustic models (INSTRUMENTS, used by svs5196/co2_15) are lists of partials (ratio, amplitude, decay 1/s;
0 = held), attack / release (s), ring = length of a struck note (s), vib = (rate Hz, depth),
trem = (rate Hz, depth), breath = air noise level.

Electronic models (ELECTRONIC, used by svs5313/nightlights_grid_and_regions) are small synth voices:
    wave     "saw" | "square" | "pulse" | "sine" (band-limited, built from harmonics) or "fm" (2-operator FM)
    detune   cents of each unison oscillator (several = a thick, chorused sound)
    duty     pulse width 0..1, pwm = (rate Hz, depth) slowly sweeps it
    max_harm highest harmonic (few = a lo-fi chip sound)
    cutoff   (start, end, decay 1/s) of a low-pass filter envelope, in multiples of the note's frequency;
             res = resonant peak at the cutoff
    fm       (modulator ratio, start index, end index, index decay 1/s): bright attack that mellows
    decay    amplitude decay 1/s (0 = held), drive = soft saturation, bits = amplitude quantisation
Struck instruments ring for their own `ring` whatever note length is asked for; sustained ones last `dur`.
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
    "cello":      dict(struck=False, attack=0.18, release=0.35, vib=(5.0, 0.004),
                       parts=[(k, 1 / k ** 1.3 * (1.3 if k in (2, 3) else 1.0), 0) for k in range(1, 11)]),
    "flute":      dict(struck=False, attack=0.09, release=0.25, vib=(5.0, 0.003), breath=0.05,
                       parts=[(1, 1.0, 0), (2, 0.22, 0), (3, 0.08, 0)]),
    "oboe":       dict(struck=False, attack=0.05, release=0.18, vib=(5.5, 0.003),
                       parts=[(1, 0.45, 0), (2, 1.0, 0), (3, 0.80, 0), (4, 0.55, 0), (5, 0.35, 0),
                              (6, 0.20, 0), (7, 0.12, 0)]),
}


ELECTRONIC = {
    # struck
    "synth_pluck": dict(struck=True, ring=0.9, wave="saw", detune=(-7, 7), cutoff=(16, 1.5, 10), res=0.8,
                        attack=0.002, decay=3.5, release=0.08),
    "chip":        dict(struck=True, ring=0.32, wave="pulse", duty=0.25, max_harm=9,
                        attack=0.001, decay=7.0, release=0.03),
    "fm_piano":    dict(struck=True, ring=2.0, wave="fm", fm=(1.0, 2.6, 0.25, 4.0), trem=(4.5, 0.15),
                        attack=0.002, decay=1.3, release=0.20),
    "fm_glass":    dict(struck=True, ring=1.6, wave="fm", fm=(4.0, 3.0, 0.15, 6.0),
                        attack=0.001, decay=2.2, release=0.15),
    # sustained
    "pulse_lead":  dict(struck=False, wave="pulse", duty=0.30, pwm=(0.45, 0.15), cutoff=(9, 5, 6), res=0.3,
                        vib=(5.2, 0.003), attack=0.03, release=0.15),
    "theremin":    dict(struck=False, wave="sine", vib=(5.5, 0.008), drive=1.8, attack=0.12, release=0.30),
    "saw_bass":    dict(struck=False, wave="saw", detune=(-9, 0, 9), cutoff=(8, 2.5, 4), res=0.4, drive=1.3,
                        attack=0.02, release=0.20),
}
MAX_HARMONICS = 32
_cache: dict = {}


def _spec(inst: str) -> dict:
    return INSTRUMENTS[inst] if inst in INSTRUMENTS else ELECTRONIC[inst]


def is_struck(inst: str) -> bool:
    return _spec(inst)["struck"]


def _electronic(spec: dict, freq: float, dur: float, sr: int) -> np.ndarray:
    n = max(1, int((spec["ring"] if spec["struck"] else dur) * sr))
    t = np.arange(n) / sr
    rate, depth = spec.get("vib", (0.0, 0.0))
    vib = np.cumsum(1 + depth * np.sin(2 * np.pi * rate * t)) / sr
    wave = spec["wave"]
    if "cutoff" in spec:
        c0, c1, cd = spec["cutoff"]
        fc = freq * (c1 + (c0 - c1) * np.exp(-cd * t))
    duty = spec.get("duty", 0.5)
    if "pwm" in spec:
        duty = duty + spec["pwm"][1] * np.sin(2 * np.pi * spec["pwm"][0] * t)
    detune = spec.get("detune", (0,))
    y = np.zeros(n)
    for i, cents in enumerate(detune):
        f = freq * 2 ** (cents / 1200)
        phase = 2 * np.pi * f * vib + 1.3 * i          # different start phase per unison voice
        if wave == "fm":
            ratio, i0, i1, idecay = spec["fm"]
            index = i1 + (i0 - i1) * np.exp(-idecay * t)
            y += np.sin(phase + index * np.sin(ratio * phase))
            continue
        top = 1 if wave == "sine" else min(spec.get("max_harm", MAX_HARMONICS), int(sr / 2 / f))
        if "cutoff" in spec:
            r = f / fc
            r4, r_lo, r_hi = r ** 4, float(r.min()), float(r.max())
        # cos(k*phase) by the Chebyshev recurrence: one multiply-add per harmonic instead of a cos()
        c_prev, c_k = np.ones(n), np.cos(phase)
        two_c = 2 * c_k
        for k in range(1, top + 1):
            if k > 1:
                c_prev, c_k = c_k, two_c * c_k - c_prev
            if wave == "saw":
                a = 1 / k
            elif wave == "square":
                if k % 2 == 0:
                    continue
                a = 1 / k
            elif wave == "pulse":
                a = np.sin(np.pi * k * duty) / k
            else:
                a = 1.0
            if "cutoff" in spec:                     # 12 dB/octave low-pass + resonant bump at the cutoff
                g = 1 / np.sqrt(1 + k ** 4 * r4)
                if spec.get("res") and k * r_lo < 1.75 and k * r_hi > 0.25:
                    g = g + spec["res"] * np.exp(-((k * r - 1) / 0.25) ** 2)
                a = a * g
            y += a * c_k
    y /= len(detune)
    if spec.get("drive"):
        y = np.tanh(spec["drive"] * y) / np.tanh(spec["drive"])
    env = np.minimum(1.0, t / spec["attack"])
    if spec.get("decay"):
        env *= np.exp(-spec["decay"] * t)
    rel = min(n, int(spec["release"] * sr))
    if rel:
        env[-rel:] *= np.linspace(1, 0, rel)
    if "trem" in spec:
        r, d = spec["trem"]
        env *= 1 - d * (0.5 - 0.5 * np.cos(2 * np.pi * r * t))
    y = y / (np.max(np.abs(y)) or 1.0) * env
    if spec.get("bits"):
        steps = 2 ** (spec["bits"] - 1)
        y = np.round(y * steps) / steps
    return y


def tone(inst: str, freq: float, dur: float, sr: int = synth.SR) -> np.ndarray:
    """One note of an instrument model, mono, `dur` seconds (struck notes ring for their own `ring`)."""
    if inst in ELECTRONIC:                           # cached: struck notes repeat a lot
        spec = ELECTRONIC[inst]
        key = (inst, round(freq, 3), 0.0 if spec["struck"] else round(dur, 3), sr)
        if key not in _cache:
            if len(_cache) > 2000:
                _cache.clear()
            _cache[key] = _electronic(spec, freq, dur, sr)
        return _cache[key].copy()
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
