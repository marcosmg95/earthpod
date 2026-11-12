"""Data -> music mapping. Every note is traceable to one measured value.

Headline rule (say it in the pitch): one year = one note; each 0.1 degC of global
warming raises the melody one step of a D minor pentatonic scale; 0 degC (the
1951-1980 average) is the tonic, which a low drone holds as a reference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

SCALE = [0, 3, 5, 7, 10]  # minor pentatonic, semitones above the tonic
TONIC_MIDI = 50           # D3 = 0 degC for the lead melody
MIDI_MIN, MIDI_MAX = 36, 96


@dataclass
class Voice:
    name: str
    column: str              # source series name
    step_c: float            # degC per scale step
    tonic_midi: int          # MIDI note for 0 degC
    pan: float               # -1 (left) .. +1 (right)
    timbre: str              # "pluck" | "string" | "soft"
    gain: float
    smooth: float = 0.0      # EMA alpha (0 = no smoothing)


DEFAULT_VOICES = [
    Voice("Global", "global", 0.10, TONIC_MIDI, 0.0, "pluck", 0.9),
    Voice("Arctic", "64N-90N", 0.35, TONIC_MIDI + 24, -0.6, "string", 0.35, 0.3),
    Voice("Northern mid-latitudes", "44N-64N", 0.20, TONIC_MIDI + 12, -0.25, "string", 0.25, 0.3),
    Voice("Tropics", "24S-24N", 0.15, TONIC_MIDI, 0.25, "string", 0.25, 0.3),
    Voice("Southern extratropics", "90S-24S", 0.15, TONIC_MIDI, 0.6, "string", 0.25, 0.3),
]


@dataclass
class Note:
    start: float
    dur: float
    midi: float
    vel: float
    pan: float
    timbre: str
    voice: str
    year: int
    value: float

    @property
    def freq(self) -> float:
        return midi_to_hz(self.midi)


@dataclass
class YearInfo:
    year: int
    start: float
    dur: float
    values: dict = field(default_factory=dict)
    midi: dict = field(default_factory=dict)
    record: bool = False
    dissonant: bool = False
    description: str = ""


def midi_to_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def value_to_degree(value_c: float, step_c: float) -> int:
    return int(np.round(value_c / step_c))


def degree_to_midi(degree: int, tonic_midi: int) -> int:
    octave, idx = divmod(degree, len(SCALE))
    return int(np.clip(tonic_midi + 12 * octave + SCALE[idx], MIDI_MIN, MIDI_MAX))


def value_to_midi(value_c: float, step_c: float, tonic_midi: int) -> int:
    return degree_to_midi(value_to_degree(value_c, step_c), tonic_midi)


def ema(s: pd.Series, alpha: float) -> pd.Series:
    return s if alpha <= 0 else s.ewm(alpha=alpha, adjust=False).mean()


def tempo_bpm(series: pd.Series, lo=72.0, hi=132.0, window=10) -> pd.Series:
    """Faster when warming is faster: |change over `window` years| -> BPM, smoothed."""
    rate = series.diff(window).abs().fillna(0) / window * 10  # degC per decade
    rate = ema(rate, 0.2)
    t = np.clip(rate / 0.30, 0, 1)                            # 0.3 degC/decade = top speed
    return lo + (hi - lo) * t


def build_score(
    data: pd.DataFrame,
    voices: list[Voice] = DEFAULT_VOICES,
    years: tuple[int, int] | None = None,
    dissonance_above_c: float = 1.0,
    record_from: int = 1900,
) -> tuple[list[Note], list[YearInfo], float]:
    """data: DataFrame indexed by Year with a 'global' column plus zone columns."""
    df = data.copy()
    if years:
        df = df.loc[years[0]:years[1]]
    df = df.dropna(subset=["global"])
    g = df["global"]
    bpm = tempo_bpm(g)

    smoothed = {v.name: ema(df[v.column], v.smooth) for v in voices if v.column in df}
    notes: list[Note] = []
    info: list[YearInfo] = []
    t = 0.0
    running_max = -np.inf
    for year, row in df.iterrows():
        beat = 60.0 / float(bpm.loc[year])
        yi = YearInfo(year=int(year), start=t, dur=beat)
        for v in voices:
            if v.name not in smoothed or pd.isna(smoothed[v.name].loc[year]):
                continue
            val = float(smoothed[v.name].loc[year])
            midi = value_to_midi(val, v.step_c, v.tonic_midi)
            yi.values[v.name] = round(float(row[v.column]), 2)
            yi.midi[v.name] = midi
            lead = v.name == "Global"
            notes.append(Note(t, beat * (0.9 if lead else 1.6), midi, v.gain,
                              v.pan, v.timbre, v.name, int(year), val))
        gval = float(g.loc[year])
        if gval > running_max and year >= record_from:
            yi.record = True
        running_max = max(running_max, gval)
        if gval > dissonance_above_c:
            yi.dissonant = True  # add a tritone above the lead: audible "alarm"
            notes.append(Note(t, beat * 0.9, yi.midi["Global"] + 6, 0.25, 0.1,
                              "pluck", "Dissonance", int(year), gval))
        if yi.record:
            notes.append(Note(t, beat * 3, yi.midi["Global"] + 24, 0.3, 0.0,
                              "bell", "Record", int(year), gval))
        yi.description = describe(yi)
        info.append(yi)
        t += beat
    return notes, info, t


def describe(yi: YearInfo) -> str:
    parts = [f"{yi.year}: planet {yi.values.get('Global', float('nan')):+.2f} °C"]
    if "Arctic" in yi.values:
        parts.append(f"Arctic {yi.values['Arctic']:+.1f} °C")
    if "Barcelona" in yi.values:
        parts.append(f"Barcelona region {yi.values['Barcelona']:+.1f} °C")
    if yi.record:
        parts.append("warmest year so far")
    return ", ".join(parts)


MAPPING_TEXT = (
    "One year is one note. Each 0.1 °C of global warming raises the melody one step of a "
    "D minor pentatonic scale; the low drone is 0 °C, the 1951–1980 average. Strings are "
    "latitude bands, with the Arctic highest. Tempo speeds up when warming speeds up, a "
    "clashing note sounds above +1 °C, and a bell marks each new record year."
)


def score_to_dict(notes, info, duration, voices=DEFAULT_VOICES) -> dict:
    return {
        "mapping": MAPPING_TEXT,
        "duration_s": round(duration, 3),
        "voices": [asdict(v) for v in voices],
        "years": [asdict(y) for y in info],
    }
