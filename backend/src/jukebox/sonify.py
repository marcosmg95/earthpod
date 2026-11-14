"""Video-locked data sonification: a timeline (movie frame -> data label) and the script contract.

A sonification script is a plain .py file in backend/sonifications/svs<id>/ (shown only for that SVS page;
files directly in backend/sonifications/ are generic and shown for every page) with:

    TITLE = "Short name"
    DESCRIPTION = "One sentence: what data, what mapping."
    def render(ctx: SonifyContext) -> np.ndarray:   # stereo float, shape (n, 2), at ctx.sr
    PARAMS = {"GAIN": (0.0, 1.0)}                   # optional: tunable constants -> (min, max); see Param

Sample 0 of the returned audio plays at video time 0; run() pads/trims it to the movie length.

Stem scripts (live levels in the explorer): render() returns named layers instead of one array,
and STEMS says which PARAMS constant sets each layer's level; OUTPUT_GAIN (optional) is the level
after the mix. render() must not use those constants itself: the mix (see Stems) applies them, so
moving their sliders changes the sound in the player at once, without running the script again.

    STEMS = {"breath": "BREATH_GAIN", "heart": "HEART_GAIN"}
    def render(ctx):
        return {"breath": breath, "heart": heart}         # each (n, 2), within [-1, 1]
"""
from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd

from . import frames, mapping, nightlights_frames, synth

MAX_DURATION_S = 120.0  # keeps the base64 WAV in the page at a sane size (~20 MB)


def label_year(label: str) -> int | None:
    """'1998' / '1998.0' / '1998.5' -> 1998 (same rule as data.load_frame_years); else None."""
    try:
        return int(float(label))
    except ValueError:
        return None


@dataclass
class Timeline:
    """One label per movie frame; frame i is on screen from i/fps to (i+1)/fps."""
    labels: list[str]
    fps: float

    @property
    def duration(self) -> float:
        return len(self.labels) / self.fps

    def time_of(self, frame: int) -> float:
        return frame / self.fps

    def spans(self) -> list[tuple[str, float, float]]:
        """Runs of the same label -> (label, t0, t1)."""
        out: list[tuple[str, float, float]] = []
        start = 0
        for i in range(1, len(self.labels) + 1):
            if i == len(self.labels) or self.labels[i] != self.labels[start]:
                out.append((self.labels[start], self.time_of(start), self.time_of(i)))
                start = i
        return out

    @classmethod
    def linear(cls, start_year: int, end_year: int, duration_s: float, fps: float) -> "Timeline":
        """Fallback when the page has no time.txt: years spread evenly over the movie."""
        n = max(1, round(duration_s * fps))
        years = np.linspace(start_year, end_year + 1, n, endpoint=False).astype(int)
        return cls([str(y) for y in years], fps)


@dataclass
class SonifyContext:
    viz_id: int
    timeline: Timeline
    data: dict = field(default_factory=dict)  # raw SVS JSON of the page
    sr: int = synth.SR
    movie: str = ""                           # filename of the movie the audio will play with
    params: dict = field(default_factory=dict)  # overrides for the scripts' PARAMS constants (see Param)

    @property
    def duration(self) -> float:
        return self.timeline.duration

    @property
    def n_samples(self) -> int:
        return int(round(self.duration * self.sr))

    @property
    def frame_times(self) -> np.ndarray:
        """Video time (s) at which each movie frame appears."""
        return np.arange(len(self.timeline.labels)) / self.timeline.fps

    def frame_features(self) -> frames.FrameFeatures:
        """Colour features measured from this movie, one row per frame (see jukebox.frames)."""
        f = frames.load(self.viz_id, self.movie)
        if f is None:
            raise LookupError(f"No frame features for SVS {self.viz_id} movie {self.movie!r}. This script needs "
                              "one of the SVS 5196 movies measured by scripts/poc6_svs5196_features.py.")
        if len(f.table) != len(self.timeline.labels):
            raise ValueError(f"The timeline has {len(self.timeline.labels)} frames but the movie was measured "
                             f"with {len(f.table)}: use the timeline the explorer builds from the frame features.")
        return f

    def nightlights_features(self) -> nightlights_frames.NightLightsFeatures:
        """Screen-space features for the measured SVS 5313 EIC movie."""
        f = nightlights_frames.load(self.viz_id, self.movie)
        if f is None:
            raise LookupError("Night-lights features require the SVS 5313 2160p30 H.265 EIC movie.")
        if len(f.table) != len(self.timeline.labels) or not np.isclose(self.timeline.fps, nightlights_frames.FPS):
            raise ValueError("Night-lights features require the movie's 1300-frame timeline at 30 fps.")
        return f

    def nightlights_grids(self) -> dict[str, np.ndarray]:
        """Coarse world / zoom-box light grids of the measured SVS 5313 EIC movie (nightlights_frames.GRID_KEYS)."""
        g = nightlights_frames.load_grids(self.viz_id, self.movie)
        if g is None:
            raise LookupError("Night-lights grids require the SVS 5313 EIC movie: run scripts/poc7_svs5313_features.py.")
        return g

    def notes_from_series(self, series: pd.Series, voice: mapping.Voice,
                          vel: float | None = None, min_dur: float = 0.12) -> list[mapping.Note]:
        """One note per timeline span whose label is a year in `series` (index = int year).

        The note starts when that year appears on screen and lasts while it stays there;
        pitch uses the jukebox rule (mapping.value_to_midi with the voice's step and tonic).
        """
        notes = []
        for label, t0, t1 in self.timeline.spans():
            year = label_year(label)
            if year is None or year not in series.index or pd.isna(series.loc[year]):
                continue
            value = float(series.loc[year])
            notes.append(mapping.Note(
                start=t0, dur=max(t1 - t0, min_dur),
                midi=mapping.value_to_midi(value, voice.step_c, voice.tonic_midi),
                vel=voice.gain if vel is None else vel, pan=voice.pan, timbre=voice.timbre,
                voice=voice.name, year=year, value=value,
            ))
        return notes

    def render_notes(self, notes: list[mapping.Note], **kw) -> np.ndarray:
        """synth.render over exactly the movie length (no tail); kw -> synth.render (drone_midi, ...)."""
        return synth.render(notes, self.duration, sr=self.sr, tail=0.0, **kw)


# ---- scripts -----------------------------------------------------------------

def discover(folder: Path) -> dict[str, Path]:
    """name -> path in natural numeric order (files starting with '_' are skipped)."""
    paths = sorted(Path(folder).glob("*.py"))
    paths.sort(key=lambda p: [int(part) if i % 2 else part
                             for i, part in enumerate(re.split(r"([0-9]+)", p.stem))])
    return {p.stem: p for p in paths if not p.name.startswith("_")}


def folder_for(root: Path, viz_id: int) -> Path:
    """Where the scripts for one SVS page live: <root>/svs<id>/."""
    return Path(root) / f"svs{int(viz_id)}"


def discover_for(root: Path, viz_id: int) -> dict[str, Path]:
    """Scripts offered for SVS page `viz_id`: generic ones in <root>/ (any page) + those in <root>/svs<id>/."""
    out = discover(root)
    sub = folder_for(root, viz_id)
    if sub.is_dir():
        out.update(discover(sub))
    return out


def load(path: Path) -> ModuleType:
    """Fresh import on every call, so edits to a script apply on the next Streamlit rerun."""
    spec = importlib.util.spec_from_file_location(f"sonification_{Path(path).stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "render", None)):
        raise TypeError(f"{Path(path).name} must define render(ctx) -> np.ndarray")
    return mod


@dataclass(frozen=True)
class Param:
    """A script constant that can be tuned without editing the file (sliders, `--set NAME=VALUE`)."""
    name: str
    default: float | int
    lo: float
    hi: float

    @property
    def step(self) -> float | int:
        return 1 if isinstance(self.default, int) else (self.hi - self.lo) / 200

    def coerce(self, value) -> float | int:
        return int(round(float(value))) if isinstance(self.default, int) else float(value)


def params_of(mod: ModuleType) -> dict[str, Param]:
    """The tunable constants a script declares: PARAMS = {"GAIN": (0.0, 1.0)} -> name -> (min, max).

    The current value of the module constant of that name is the default. render() must read the
    constant when it runs (not at import time) for an override to take effect.
    """
    out = {}
    for name, (lo, hi) in getattr(mod, "PARAMS", {}).items():
        if not hasattr(mod, name):
            raise AttributeError(f"PARAMS lists {name!r} but the script has no constant with that name")
        out[name] = Param(name, getattr(mod, name), lo, hi)
    return out


def apply_params(mod: ModuleType, overrides: dict) -> None:
    """Set the declared PARAMS of `mod` named in `overrides`; other names are ignored."""
    for name, p in params_of(mod).items():
        if name in overrides:
            setattr(mod, name, p.coerce(overrides[name]))


def _fit(y, n: int) -> np.ndarray:
    """Mono or stereo audio -> stereo float of exactly n samples, clipped to [-1, 1]."""
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = np.column_stack([y, y])
    if y.ndim != 2 or y.shape[1] != 2:
        raise ValueError(f"render() must return audio of shape (n, 2) or (n,), got {y.shape}")
    y = y[:n] if len(y) >= n else np.vstack([y, np.zeros((n - len(y), 2))])
    return np.clip(y, -1.0, 1.0)


@dataclass
class Stems:
    """A script's audio before the final mix (see stem scripts in the module docstring).

    A plain script gives one stem, "mix", played as is. A stem script gives named layers; the mix is
    their sum weighted by `gains`, peak-normalised (-6 dB, like synth.normalize) and times `output`.
    The explorer's player redoes this mix live in the browser, so level changes need no re-render.
    """
    audio: dict[str, np.ndarray]          # name -> (n, 2) float in [-1, 1]
    gains: dict[str, float]               # name -> level
    params: dict[str, str]                # name -> PARAMS constant that sets its level
    output: float = 1.0                   # OUTPUT_GAIN: level after normalising
    normalize: bool = False

    def mix(self, gains: dict[str, float] | None = None, output: float | None = None) -> np.ndarray:
        gains = {**self.gains, **(gains or {})}
        y = sum(gains[k] * a for k, a in self.audio.items())
        if self.normalize:
            y = synth.normalize(y) * (self.output if output is None else output)
        return np.clip(y, -1.0, 1.0)


def mix_params(mod: ModuleType) -> set[str]:
    """PARAMS of a stem script that only set levels (STEMS values and OUTPUT_GAIN): no re-render needed."""
    stems = getattr(mod, "STEMS", {})
    return set(stems.values()) | ({"OUTPUT_GAIN"} if stems and hasattr(mod, "OUTPUT_GAIN") else set())


def render_stems(path: Path, ctx: SonifyContext) -> Stems:
    """Run a script (with ctx.params applied) and return its stems, each exactly ctx.n_samples long."""
    mod = load(path)
    apply_params(mod, ctx.params)
    y = mod.render(ctx)
    n = ctx.n_samples
    if not isinstance(y, dict):
        return Stems({"mix": _fit(y, n)}, {"mix": 1.0}, {})
    table = getattr(mod, "STEMS", {})
    if missing := [k for k in table if k not in y]:
        raise ValueError(f"STEMS lists {missing} but render() returned only {list(y)}")
    if bad := [p for p in table.values() if not hasattr(mod, p)]:
        raise AttributeError(f"STEMS names {bad} but the script has no constant with that name")
    return Stems(audio={k: _fit(v, n) for k, v in y.items()},
                 gains={k: float(getattr(mod, table[k])) if k in table else 1.0 for k in y},
                 params={k: table[k] for k in y if k in table},
                 output=float(getattr(mod, "OUTPUT_GAIN", 1.0)), normalize=True)


def run(path: Path, ctx: SonifyContext) -> np.ndarray:
    """Run a script and return stereo float audio of exactly ctx.n_samples, clipped to [-1, 1]."""
    return render_stems(path, ctx).mix()
