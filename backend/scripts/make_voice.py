"""Make the arcade voice-over clips (Windows text-to-speech + 80s sampler effect).

    uv run python scripts/make_voice.py

Writes frontend/arcade/voice/*.wav. To use your own recordings, save WAVs with the same names there.
"""
from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "frontend" / "arcade" / "voice"
LINES = {
    "welcome": "Welcome, to this earthly experience.",
    "insert": "Insert a coin. Press enter, or space.",
    # the sound tour on the welcome screen: one line per element, then the music example
    "elements": "Every colour of the Earth has a voice.",
    "water": "Water sounds like this.",
    "land": "Land sounds like this.",
    "fire": "Fire sounds like this.",
    "wind": "And wind, sounds like this.",
    "discover": "Scroll down, to discover.",
    "choose": "Choose a record. Type a letter, and a number.",
}
VOICE = "Microsoft Zira Desktop"   # the only en-US voice on this machine; any installed voice works
SR = 22050


def tts(text: str, path: Path) -> None:
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"try {{ $s.SelectVoice('{VOICE}') }} catch {{}};"
        "$s.Rate = -2;"
        f"$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo({SR}, 'Sixteen', 'Mono');"
        f"$s.SetOutputToWaveFile('{path}', $f);"
        f"$s.Speak('{text}'); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def read(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768


def write(path: Path, x: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def arcade(x: np.ndarray, pitch: float = 0.88, hold_sr: int = 7000, bits: int = 5) -> np.ndarray:
    """Deeper pitch, sample-and-hold to ~7 kHz, 5-bit quantisation, soft low-pass: an 80s speech chip."""
    x = x / (np.abs(x).max() + 1e-9)
    idx = np.arange(0, len(x) - 1, pitch)                       # slower playback = lower, deeper voice
    x = np.interp(idx, np.arange(len(x)), x)
    step = SR / hold_sr
    held = x[(np.floor(np.arange(len(x)) / step) * step).astype(int)]
    q = 2 ** (bits - 1)
    crushed = np.round(held * q) / q
    k = np.ones(3) / 3                                          # take the harsh edge off
    y = np.convolve(crushed, k, mode="same")
    tail = np.zeros(int(0.25 * SR))
    return np.concatenate([y * 0.9, tail])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in LINES.items():
            raw = Path(tmp) / f"{name}.wav"
            tts(text, raw)
            write(OUT / f"{name}.wav", arcade(read(raw)))
            print(f"  + {name}.wav  \"{text}\"")


if __name__ == "__main__":
    main()
