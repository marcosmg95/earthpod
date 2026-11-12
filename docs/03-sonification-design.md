# 03 — Sonification design

## Principle
"Every note is a measured number, and we can show you which one." One data layer per voice; a one-sentence mapping explanation everywhere (app, video, slides).

## Mapping table (draft — freeze Sat AM)
| Data feature | Sound parameter | Guardrail |
|---|---|---|
| Global anomaly (°C) | Melody pitch | Quantize to D minor pentatonic / Dorian; 1 step ≈ 0.1 °C; 0 °C = tonic reference drone |
| Rate of change (Δ/decade) | Tempo / note density | Clamp 60–140 BPM; EMA smoothing α≈0.2 |
| Zonal bands (Arctic → Antarctic) | Separate string voices | Arctic = highest voice so Arctic amplification is audible |
| East–west position (scan playhead) | Stereo pan −1…+1 | Tone.Panner per voice; never the only carrier of info (mono-compatible) |
| % area > +1 °C / extremes | Filter brightness + dissonance (♭9, tritone, detune) | Only beyond threshold |
| Image brightness/intensity | Volume | Compress; never above −6 dBFS |
| Record-breaking year | Bell/percussion accent + spoken "record" | Sparse, earcon-style |

## Keeping it musical
- Scale quantization; fixed harmonic bed (I–VI–VII loop that darkens toward minor/diminished as anomalies grow)
- `rampTo` 50–200 ms on parameters (no zipper noise)
- Max 6 simultaneous voices

## Stack
- Static web app: Vite + TS (or React), deployed on GitHub Pages / Vercel
- Audio: Tone.js (Transport, PolySynth, Sampler, Panner, filters). AudioContext starts on user gesture.
- Offline prep in Python: ffmpeg/curl frames → downsample (~360x180); xarray/pandas → `tracks.json` (global, 4 zonal bands, Barcelona, per-frame features)
- Browser only plays precomputed JSON + low-res frames (keeps risk out of the live demo)
- Hover mode: Canvas `getImageData` + LUT
- Offline playlist renders (optional): STRAUSS
- Avoid generative music models live: MusicGen weights are CC-BY-NC 4.0 and need ~16 GB GPU. At most a pre-rendered, labelled background.
- VLM for alt text: offline only, human-reviewed, grounded in the computed numbers.

## Prior art to cite / learn from
- NASA Chandra "A Universe of Sound" — scan metaphor, one layer per instrument, co-designed with blind consultant; evaluation with 3,184 respondents (Arcand et al., Frontiers in Communication 2024). https://chandra.si.edu/sound/
- "A Song of Our Warming Planet" (Crawford, 2013) — GISTEMP on cello, one note per year, ~0.03 °C per semitone; follow-up "Planetary Bands, Warming World" with one instrument per latitude band.
- Highcharts Sonification Studio (Georgia Tech Sonification Lab) — accessible audio graphs.
- Microsoft Chart Reader (CHI 2023) — pitch to relative axis position works for blind users.
- Review arXiv 2402.16558 — spoken intro + non-speech audio helps; inexperience causes misreadings.
