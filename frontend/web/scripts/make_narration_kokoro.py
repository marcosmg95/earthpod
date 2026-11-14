#!/usr/bin/env python3
"""Make the intro narration with Kokoro (open-weight, Apache-2.0 text-to-speech).

    source .venv-tts/bin/activate
    python scripts/make_narration_kokoro.py
    python scripts/make_narration_kokoro.py --voice bf_emma --lang b --speed 0.9

Writes public/intro/narration.m4a and public/intro/narration.vtt. Needs ffmpeg.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

# keep in step with NARRATION in src/routes/Intro.tsx
LINES = [
    "I was born 4.54 billion years ago.",
    "300,000 years ago, I provided shelter to humans.",
    "Since then, we have shared countless experiences and witnessed many changes.",
    "This is our current era.",
]

p = argparse.ArgumentParser()
p.add_argument("--voice", default="af_heart", help="e.g. af_heart, af_bella, bf_emma, am_michael, bm_george")
p.add_argument("--lang", default="a", help="a = American English, b = British English (must match the voice)")
p.add_argument("--speed", type=float, default=0.9, help="1.0 = normal; a little slower sounds calmer")
p.add_argument("--gap", type=float, default=1.2, help="seconds of silence between lines")
p.add_argument("--lead", type=float, default=2.0, help="seconds of black before the first line")
p.add_argument("--pitch", type=float, default=0.0, help="semitones; -2 to -3 sounds older and deeper")
p.add_argument("--room", default="empty", choices=["none", "small", "empty", "hall"])
p.add_argument("--wet", type=float, default=1.0, help="how much room: 0.5 subtle, 1 normal, 1.5 a lot")
p.add_argument("--ir", help="optional impulse response .wav of a real room (replaces --room)")
a = p.parse_args()

SR = 24000  # Kokoro's sample rate
out = Path(__file__).resolve().parent.parent / "public" / "intro"
out.mkdir(parents=True, exist_ok=True)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def ts(s: float) -> str:
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:06.3f}"


def to_numpy(audio) -> np.ndarray:
    return (audio.cpu().numpy() if hasattr(audio, "cpu") else np.asarray(audio)).astype(np.float32)

# early reflections in ms, set differently left and right so the room feels wide
ROOMS = {
    "small": ([11, 23, 37, 53], [17, 29, 43, 61], [0.30, 0.22, 0.15, 0.10]),
    "empty": ([19, 43, 71, 113, 167, 241, 337], [29, 53, 83, 131, 191, 263, 359],
              [0.42, 0.35, 0.28, 0.22, 0.17, 0.12, 0.08]),
    "hall": ([31, 67, 109, 173, 251, 353, 487, 631], [41, 79, 127, 191, 277, 389, 523, 677],
             [0.45, 0.38, 0.31, 0.25, 0.19, 0.14, 0.10, 0.06]),
}


def taps(delays: list[int], decays: list[float]) -> str:
    d = "|".join(str(x) for x in delays)
    g = "|".join(f"{min(0.9, x * a.wet):.3f}" for x in decays)
    return f"aecho=0.8:0.55:{d}:{g}"

pipeline = KPipeline(lang_code=a.lang)
parts = [silence(a.lead)]
pos = len(parts[0])
cues = []
for line in LINES:
    speech = np.concatenate([to_numpy(audio) for _, _, audio in pipeline(line, voice=a.voice, speed=a.speed)])
    start = pos / SR
    parts.append(speech)
    pos += len(speech)
    cues.append((start, pos / SR + a.gap * 0.8, line))
    gap = silence(a.gap)
    parts.append(gap)
    pos += len(gap)
parts.append(silence(1.0))

with tempfile.TemporaryDirectory() as tmp:
    wav = Path(tmp) / "narration.wav"
    sf.write(wav, np.concatenate(parts), SR)

    r = 2 ** (a.pitch / 12)
    shift = f"asetrate={SR * r:.0f},aresample={SR},atempo={1 / r:.4f}," if a.pitch else ""
    finish = "highpass=f=70,alimiter=limit=0.9"
    inputs = ["-i", str(wav)]

    if a.ir:  # a real room
        inputs += ["-i", a.ir]
        graph = (f"[0:a]{shift}pan=stereo|c0=c0|c1=c0,asplit[dry][x];"
                 f"[1:a]aresample={SR}[ir];[x][ir]afir[room];"
                 f"[dry][room]amix=inputs=2:weights='1 {0.35 * a.wet:.2f}':normalize=0,{finish}[out]")
    elif a.room != "none":  # a synthetic room, wider left/right
        left, right, decays = ROOMS[a.room]
        graph = (f"[0:a]{shift}asplit[l][r];"
                 f"[l]{taps(left, decays)}[lw];[r]{taps(right, decays)}[rw];"
                 f"[lw][rw]join=inputs=2:channel_layout=stereo,{finish}[out]")
    else:
        graph = f"[0:a]{shift}pan=stereo|c0=c0|c1=c0,{finish}[out]"

    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]",
                    "-c:a", "aac", "-b:a", "192k", str(out / "narration.m4a")], check=True)

vtt = ["WEBVTT", ""]
for start, end, line in cues:
    vtt += [f"{ts(start)} --> {ts(end)}", line, ""]
(out / "narration.vtt").write_text("\n".join(vtt))
print(f"wrote {out / 'narration.m4a'} and {out / 'narration.vtt'}")