"""Video-locked data sonification: a timeline (movie frame -> data label) and the script contract.

A sonification script is a plain .py file in backend/sonifications/ with:

    TITLE = "Short name"
    DESCRIPTION = "One sentence: what data, what mapping."
    def render(ctx: SonifyContext) -> np.ndarray:   # stereo float, shape (n, 2), at ctx.sr

Sample 0 of the returned audio plays at video time 0; run() pads/trims it to the movie length.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd

from . import frames, mapping, synth

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
    """name -> path for every sonification script (files starting with '_' are skipped)."""
    return {p.stem: p for p in sorted(Path(folder).glob("*.py")) if not p.name.startswith("_")}


def load(path: Path) -> ModuleType:
    """Fresh import on every call, so edits to a script apply on the next Streamlit rerun."""
    spec = importlib.util.spec_from_file_location(f"sonification_{Path(path).stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "render", None)):
        raise TypeError(f"{Path(path).name} must define render(ctx) -> np.ndarray")
    return mod


def run(path: Path, ctx: SonifyContext) -> np.ndarray:
    """Run a script and return stereo float audio of exactly ctx.n_samples, clipped to [-1, 1]."""
    y = np.asarray(load(path).render(ctx), dtype=float)
    if y.ndim == 1:
        y = np.column_stack([y, y])
    if y.ndim != 2 or y.shape[1] != 2:
        raise ValueError(f"render() must return shape (n, 2) or (n,), got {y.shape}")
    n = ctx.n_samples
    y = y[:n] if len(y) >= n else np.vstack([y, np.zeros((n - len(y), 2))])
    return np.clip(y, -1.0, 1.0)
