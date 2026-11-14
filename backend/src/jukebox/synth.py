"""Tiny numpy synthesizer: renders a list of Notes to a stereo WAV (no audio deps)."""
from __future__ import annotations

import io
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


# ---- building blocks for sonification scripts (noise, panning, mixing) ----------------------

def band_noise(n: int, lo: float, hi: float, sr: int = SR, seed: int = 0) -> np.ndarray:
    """n samples of noise limited to lo..hi Hz, peak 1 (same seed -> same sound)."""
    spec = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / sr)
    edge = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))   # smooth 0..1 step
    spec *= edge((f - lo * 0.8) / (lo * 0.2 + 1e-9)) * edge((hi * 1.25 - f) / (hi * 0.25))
    y = np.fft.irfft(spec, n)
    return y / (np.max(np.abs(y)) or 1.0)


def pan_stereo(mono: np.ndarray, pan) -> np.ndarray:
    """Equal-power pan; `pan` is -1 (left) .. +1 (right), a number or one value per sample."""
    theta = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.column_stack([mono * np.cos(theta), mono * np.sin(theta)])


def add_at(out: np.ndarray, y: np.ndarray, t: float, sr: int = SR) -> None:
    """Mix y (mono or stereo) into the stereo buffer `out`, starting at time t; the end is cut off."""
    i0 = int(round(t * sr))
    i1 = min(len(out), i0 + len(y))
    if i0 < 0 or i1 <= i0:
        return
    out[i0:i1] += y[: i1 - i0] if y.ndim == 2 else y[: i1 - i0, None]


def normalize(stereo: np.ndarray, db: float = -6.0) -> np.ndarray:
    """Peak-normalize (silence stays silence)."""
    peak = np.max(np.abs(stereo)) or 1.0
    return stereo / peak * 10 ** (db / 20)


def _write_pcm(target, stereo: np.ndarray, sr: int) -> None:
    """16-bit stereo PCM to a path or a binary file object."""
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(target, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def write_wav(path: str | Path, stereo: np.ndarray, sr: int = SR) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_pcm(str(path), stereo, sr)
    return path


def wav_bytes(stereo: np.ndarray, sr: int = SR) -> bytes:
    """Same as write_wav, in memory (for the Streamlit player / downloads)."""
    buf = io.BytesIO()
    _write_pcm(buf, stereo, sr)
    return buf.getvalue()
