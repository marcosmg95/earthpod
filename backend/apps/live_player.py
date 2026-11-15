"""Live sonification player: the <video> is the master clock, the sonification's stems follow it.

It is a Streamlit component that stays mounted (not an st.iframe rebuilt on every change): when a re-render sends new audio, it swaps in at the current position without stopping the
video, and the level sliders of a stem script (STEMS / OUTPUT_GAIN) mix the stems in the browser at
once. The frontend is plain HTML/JS in live_player/index.html (no build step).
"""
from __future__ import annotations

import io
import wave
from pathlib import Path

import numpy as np
import streamlit.components.v1 as components

from jukebox import sonify, synth

_component = components.declare_component("live_player", path=str(Path(__file__).with_name("live_player")))


def stem_wavs(stems: sonify.Stems, sr: int) -> dict[str, bytes]:
    """Each stem as a 16-bit stereo WAV (what the browser plays)."""
    return {name: synth.wav_bytes(a, sr) for name, a in stems.audio.items()}


def wav_to_array(wav: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(wav)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    return pcm.reshape(-1, 2).astype(float) / 32767


def mix_wav(wavs: dict[str, bytes], gains: dict[str, float], output: float, normalize: bool, sr: int) -> bytes:
    """The same mix the player hears (sonify.Stems.mix), as a WAV for download."""
    if not normalize and len(wavs) == 1:
        return next(iter(wavs.values()))             # a plain script: its audio as rendered
    stems = sonify.Stems({k: wav_to_array(v) for k, v in wavs.items()},
                         {k: gains.get(k, 1.0) for k in wavs}, {}, output, normalize)
    return synth.wav_bytes(stems.mix(), sr)


def mix_spec(stems: sonify.Stems, specs: dict[str, sonify.Param], values: dict) -> dict:
    """What the player's level sliders show: one per stem with a level constant, plus OUTPUT_GAIN."""
    def slider(param: str) -> dict:
        p = specs.get(param)
        lo, hi = (p.lo, p.hi) if p else (0.0, 1.5)
        return {"param": param, "value": float(values.get(param, p.default if p else 1.0)), "lo": lo, "hi": hi}
    sliders = [{"stem": k, **slider(param)} for k, param in stems.params.items()]
    out = slider("OUTPUT_GAIN") if stems.normalize and "OUTPUT_GAIN" in specs else None
    return {"stems": sliders, "output": out}


def live_player(video_url: str, wavs: dict[str, bytes], audio_id: str, mix: dict, mix_id: str, normalize: bool,
                spans: list[tuple[str, float, float]], audio_s: float, *, aspect: float = 16 / 9,
                width_px: int = 900, chapters: list[tuple[str, float]] = (), still: bool = False,
                key: str = "live_player") -> dict | None:
    """Show the player; returns the level values the user set in it ({PARAM: value}) or None.

    still=True: `video_url` is an image, played as a scan (a line moves across it; play button + slider).

    `audio_id` changes when the audio is new (the player then swaps it in at the current time);
    `mix_id` changes when the sliders should reset to `mix` (another script or script defaults).
    """
    video_h = int(min(width_px / max(aspect, 0.3), 640))
    names = list(wavs)
    return _component(
        video_url=video_url, video_h=video_h, audio_id=audio_id, stem_names=names, normalize=normalize,
        mix=mix, mix_id=mix_id, spans=[[l, round(t0, 4), round(t1, 4)] for l, t0, t1 in spans],
        audio_s=round(audio_s, 4), chapters=[[title, round(t0, 4)] for title, t0 in chapters], still=still,
        **{f"stem_{i}": wavs[n] for i, n in enumerate(names)}, key=key, default=None)
