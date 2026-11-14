#!/usr/bin/env python3
"""Make the intro narration with the Mac's built-in text-to-speech.

    python3 scripts/make_narration.py
    python3 scripts/make_narration.py --voice "Zoe (Premium)" --rate 145

Writes public/intro/narration.m4a and public/intro/narration.vtt (captions timed to the voice).
Needs macOS `say` and ffmpeg. List voices with: say -v '?'
"""
import argparse
import subprocess
import tempfile
import wave
from pathlib import Path

# keep in step with NARRATION in src/routes/Intro.tsx
LINES = [
    "I was born 4.54 billion years ago.",
    "300,000 years ago, I provided shelter to humans.",
    "Since then, we have shared countless experiences and witnessed many changes.",
    "This is our current era.",
]

p = argparse.ArgumentParser()
p.add_argument("--voice", default="Daniel")
p.add_argument("--rate", type=int, default=150, help="words per minute")
p.add_argument("--gap", type=float, default=1.2, help="seconds of silence between lines")
p.add_argument("--lead", type=float, default=2.0, help="seconds of black before the first line")
a = p.parse_args()

RATE = 44100
out = Path(__file__).resolve().parent.parent / "public" / "intro"
out.mkdir(parents=True, exist_ok=True)


def silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(seconds * RATE)


def ts(s: float) -> str:
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:06.3f}"


with tempfile.TemporaryDirectory() as tmp:
    pcm = bytearray(silence(a.lead))
    cues = []
    for i, line in enumerate(LINES):
        f = Path(tmp) / f"{i}.wav"
        subprocess.run(["say", "-v", a.voice, "-r", str(a.rate), "--file-format=WAVE",
                        "--data-format=LEI16@44100", "-o", str(f), line], check=True)
        with wave.open(str(f)) as w:
            frames = w.readframes(w.getnframes())
        start = len(pcm) / 2 / RATE
        pcm += frames
        end = len(pcm) / 2 / RATE
        cues.append((start, end + a.gap * 0.8, line))
        pcm += silence(a.gap)
    pcm += silence(1.0)

    full = Path(tmp) / "narration.wav"
    with wave.open(str(full), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(pcm))
    # a little space around the voice; it does not change the timing
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-af", "aecho=0.8:0.55:90:0.22,highpass=f=70",
                    "-c:a", "aac", "-b:a", "160k", str(out / "narration.m4a")], check=True)

vtt = ["WEBVTT", ""]
for start, end, line in cues:
    vtt += [f"{ts(start)} --> {ts(end)}", line, ""]
(out / "narration.vtt").write_text("\n".join(vtt))
print(f"wrote {out / 'narration.m4a'} and {out / 'narration.vtt'}")