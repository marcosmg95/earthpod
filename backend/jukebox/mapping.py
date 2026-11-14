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


# --- Night lights (NASA Black Marble, data behind SVS 5313) -------------------------------
# Same Voice type; here step_c is "% light change per scale step" and the tonic is the 2012 level.
NIGHT_TONIC_MIDI = 62  # D4 = each city's 2012 glow
NIGHT_VOICES = [
    Voice("Barcelona", "barcelona", 2.0, NIGHT_TONIC_MIDI, 0.0, "pluck", 0.9),
    Voice("Kyiv", "kyiv", 5.0, NIGHT_TONIC_MIDI + 12, 0.5, "string", 0.45),
]
NIGHT_NAMES = {"barcelona": "Barcelona", "kyiv": "Kyiv", "delhi": "Delhi"}


def build_night_track(pct: pd.DataFrame, voices: list[Voice] = NIGHT_VOICES,
                      bpm: float = 60.0, alarm_drop_pct: float = 20.0) -> dict:
    """pct: % change in total night light vs 2012, index = year, columns = region keys."""
    voices = [v for v in voices if v.column in pct.columns]
    level = 1.0 + pct / 100.0                      # light relative to 2012
    yoy = (level / level.shift(1) - 1.0) * 100.0   # % change vs previous year
    beat = 60.0 / bpm
    years, t = [], 0.0
    for year, row in pct.iterrows():
        yi = YearInfo(year=int(year), start=t, dur=beat)
        parts = []
        for v in voices:
            val = row[v.column]
            if pd.isna(val):
                continue
            yi.values[v.name] = round(float(val), 1)
            yi.midi[v.name] = value_to_midi(float(val), v.step_c, v.tonic_midi)
            word = "brighter" if val > 0 else "darker"
            parts.append(f"{v.name} {abs(val):.0f}% {word} than 2012" if round(val) else f"{v.name} at its 2012 level")
            drop = yoy.loc[year, v.column]
            if pd.notna(drop) and drop <= -alarm_drop_pct:
                yi.dissonant = True
                parts.append(f"{v.name} lost {abs(drop):.0f}% of its light in one year")
        yi.description = f"{yi.year}: " + ", ".join(parts)
        years.append(asdict(yi))
        t += beat

    steps = "; ".join(f"{v.name} moves one step per {v.step_c:g}%" for v in voices)
    text = ("One year is one note, from 2012 to 2023, using night-time light measured from space. "
            "Each city starts on the home note, its own 2012 glow, which the low drone holds. "
            f"The melody steps down the D minor pentatonic scale as the city gets darker and up as it gets brighter ({steps}). "
            f"A clashing note sounds when a city loses more than {alarm_drop_pct:g}% of its light in a single year. "
            "Part of a fall can be LED street lighting, which the satellite barely sees.")
    return {
        "name": "Night lights (" + ", ".join(v.name for v in voices) + ")",
        "mapping": text,
        "duration_s": round(t, 3),
        "voices": [asdict(v) for v in voices],
        "years": years,
        "reference": {"midi": NIGHT_TONIC_MIDI, "label": "Reference: each city's 2012 glow"},
        "drone_midi": NIGHT_TONIC_MIDI - 12,
        "caption": "Data: NASA Black Marble VNP46A4 (Suomi NPP VIIRS), yearly night lights; see SVS 5313. Not endorsed by NASA.",
        "chart_label": "Line chart of night-light change versus 2012, in percent",
    }


# --- Earth in layers: temperature + night lights over the years they share ----------------
# Each layer is one voice; layers are only combined for years where *every* layer was measured.
# Columns: "global", "barcelona_temp" (degC vs 1951-1980), "barcelona_light", "kyiv_light" (% vs 2012).
LAYER_VOICES = [
    Voice("Global temperature", "global", 0.10, TONIC_MIDI, 0.0, "pluck", 0.9),
    Voice("Barcelona temperature", "barcelona_temp", 0.25, TONIC_MIDI, -0.3, "string", 0.5),
    Voice("Barcelona lights", "barcelona_light", 2.0, NIGHT_TONIC_MIDI, -0.6, "soft", 0.45),
    Voice("Kyiv lights", "kyiv_light", 5.0, NIGHT_TONIC_MIDI + 12, 0.6, "soft", 0.45),
]
LAYER_UNITS = {"global": "°C", "barcelona_temp": "°C", "barcelona_light": "%", "kyiv_light": "%"}


def shared_years(*frames: pd.DataFrame) -> pd.Index:
    """Years in which every column of every frame has a value (no gap filling)."""
    idx = None
    for f in frames:
        ok = f.dropna(how="any").index
        idx = ok if idx is None else idx.intersection(ok)
    return idx.sort_values()


def build_layers_track(temp: pd.DataFrame, night: pd.DataFrame, voices: list[Voice] = LAYER_VOICES,
                       bpm: float = 40.0, alarm_drop_pct: float = 20.0, record_from: int = 1900) -> dict:
    """temp: index = year, columns 'global' and 'barcelona' (degC anomaly, full history).
    night: index = year, columns 'barcelona' and 'kyiv' (% light change vs 2012)."""
    temp = temp[["global", "barcelona"]].astype(float)
    night = night[["barcelona", "kyiv"]].astype(float)
    years_ok = shared_years(temp, night)
    if len(years_ok) == 0:
        raise ValueError("temperature and night-light layers share no year")

    # Records use the full temperature history, so 2012 is not a "record" just by being first.
    full = temp.loc[temp.index >= record_from]
    is_record = {c: full[c] > full[c].cummax().shift(1).fillna(-np.inf) for c in full}
    level = 1.0 + night / 100.0
    yoy = (level / level.shift(1) - 1.0) * 100.0

    df = pd.DataFrame({"global": temp["global"], "barcelona_temp": temp["barcelona"],
                       "barcelona_light": night["barcelona"], "kyiv_light": night["kyiv"]}).loc[years_ok]
    smoothed = {v.name: ema(df[v.column], v.smooth) for v in voices}
    beat = 60.0 / bpm
    years, events, t = [], [], 0.0
    for year, row in df.iterrows():
        yi = YearInfo(year=int(year), start=round(t, 3), dur=beat)
        for v in voices:
            yi.values[v.name] = round(float(row[v.column]), 2 if LAYER_UNITS[v.column] == "°C" else 1)
            yi.midi[v.name] = value_to_midi(float(smoothed[v.name].loc[year]), v.step_c, v.tonic_midi)
        news = []
        if bool(is_record["global"].get(year, False)):
            yi.record = True
            news.append("warmest year so far for the planet")
        if bool(is_record["barcelona"].get(year, False)):
            news.append("warmest year so far for the Barcelona region")
        for city, name in (("barcelona", "Barcelona"), ("kyiv", "Kyiv")):
            drop = yoy.loc[year, city]
            if pd.notna(drop) and drop <= -alarm_drop_pct:
                yi.dissonant = True
                news.append(f"{name} lost {abs(drop):.0f}% of its night light in one year")

        def light(col, name):
            val = row[col]
            return f"{name} {abs(val):.0f}% {'brighter' if val > 0 else 'darker'}" if round(val) else f"{name} as in 2012"
        yi.description = (f"{yi.year}: planet {row['global']:+.2f} °C, Barcelona region {row['barcelona_temp']:+.1f} °C; "
                          f"night light vs 2012: {light('barcelona_light', 'Barcelona')}, {light('kyiv_light', 'Kyiv')}"
                          + ("".join(f". {n[0].upper()}{n[1:]}" for n in news)) + ".")
        if news:
            events.append({"year": yi.year, "text": "; ".join(news)})
        years.append(asdict(yi))
        t += beat

    first, last = int(years_ok[0]), int(years_ok[-1])
    text = (f"Earth in layers, {first} to {last}: the only years in which every layer was measured. One year is one chord. "
            "Pluck: global temperature, one scale step per 0.1 °C. Strings, left: Barcelona region temperature, one step per 0.25 °C. "
            f"Soft tones: night light seen from space, Barcelona on the left (one step per 2%) and Kyiv on the right (one step per 5%), "
            f"starting from each city's {first} glow. A bell marks a record warm year for the planet; a clashing note sounds when a city "
            f"loses more than {alarm_drop_pct:g}% of its light in a single year. Turn layers on and off to hear each one alone.")
    return {
        "name": f"Earth in layers ({first}–{last})",
        "mapping": text,
        "duration_s": round(t, 3),
        "voices": [asdict(v) for v in voices],
        "years": years,
        "events": events,
        "caption": ("Data: NASA GISTEMP v4 (global and Barcelona-region temperature) and NASA Black Marble VNP46A4 "
                    "(Suomi NPP VIIRS yearly night lights; see SVS 5313). Not endorsed by NASA."),
        "chart_label": f"Line chart of the global temperature anomaly, {first} to {last}",
    }


def score_to_dict(notes, info, duration, voices=DEFAULT_VOICES) -> dict:
    return {
        "mapping": MAPPING_TEXT,
        "duration_s": round(duration, 3),
        "voices": [asdict(v) for v in voices],
        "years": [asdict(y) for y in info],
    }
