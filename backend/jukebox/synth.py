"""Tiny numpy synthesizer: renders a list of Notes to a stereo WAV (no audio deps)."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from .mapping import Note, midi_to_hz

SR = 44100

TIMBRES = {
    # harmonic amplitudes, attack, release, decay rate (1/s, 0 = sustained)
    "pluck": dict(h=[1.0, 0.45, 0.25, 0.12, 0.06], a=0.005, r=0.25, decay=3.0),
    "string": dict(h=[1.0, 0.5, 0.33, 0.25, 0.2, 0.16], a=0.25, r=0.4, decay=0.0),
    "soft": dict(h=[1.0, 0.2], a=0.05, r=0.3, decay=0.5),
}


def _envelope(n: int, a: float, r: float, decay: float, sr: int) -> np.ndarray:
    t = np.arange(n) / sr
    env = np.minimum(1.0, t / max(a, 1e-4))
    if decay:
        env *= np.exp(-decay * t)
    nr = min(n, int(r * sr))
    if nr:
        env[-nr:] *= np.linspace(1, 0, nr)
    return env


def tone(freq: float, dur: float, timbre: str, sr: int = SR) -> np.ndarray:
    n = max(1, int(dur * sr))
    t = np.arange(n) / sr
    if timbre == "bell":  # inharmonic partials, long exponential decay
        partials = [(1.0, 1.0), (2.76, 0.5), (5.4, 0.25), (8.93, 0.12)]
        y = sum(a * np.sin(2 * np.pi * freq * p * t) * np.exp(-2.5 * p ** 0.5 * t) for p, a in partials)
        return y * np.minimum(1.0, t / 0.002)
    spec = TIMBRES.get(timbre, TIMBRES["soft"])
    vib = 1 + (0.003 * np.sin(2 * np.pi * 5 * t) if timbre == "string" else 0)
    phase = 2 * np.pi * freq * np.cumsum(vib) / sr
    y = sum(a * np.sin(k * phase) for k, a in enumerate(spec["h"], start=1) if freq * k < sr / 2)
    return y * _envelope(n, spec["a"], spec["r"], spec["decay"], sr)


def render(notes: list[Note], duration: float, sr: int = SR,
           drone_midi: float | None = 38, drone_gain: float = 0.12, tail: float = 3.0) -> np.ndarray:
    """Mix notes (equal-power pan) + optional reference drone; peak-normalize to -6 dBFS."""
    n = int((duration + tail) * sr)
    out = np.zeros((n, 2))
    for note in notes:
        y = tone(note.freq, note.dur, note.timbre, sr) * note.vel
        i0 = int(note.start * sr)
        i1 = min(n, i0 + len(y))
        theta = (note.pan + 1) * np.pi / 4
        out[i0:i1, 0] += y[: i1 - i0] * np.cos(theta)
        out[i0:i1, 1] += y[: i1 - i0] * np.sin(theta)
    if drone_midi is not None:  # 0 degC reference: D2, one octave under the lead tonic
        t = np.arange(n) / sr
        f = midi_to_hz(drone_midi)
        d = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * drone_gain
        fade = np.minimum(1, np.minimum(t / 2, (t[-1] - t) / 2))
        out += (d * fade)[:, None]
    peak = np.max(np.abs(out)) or 1.0
    return out / peak * 10 ** (-6 / 20)


def write_wav(path: str | Path, stereo: np.ndarray, sr: int = SR) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path
