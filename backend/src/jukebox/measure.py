"""Measure the SVS movies the sonification scripts read: one command for every measured page.

    uv run python -m jukebox.measure              # every page
    uv run python -m jukebox.measure 5669 5196    # some pages
    uv run python -m jukebox.measure --list       # what each page downloads and writes

For each page: download its movies into data/raw/ (gitignored; resumes broken downloads) when they are missing,
measure them and write the results into data/derived/ (committed, so the explorer and the scripts need no download).
Three kinds of page share this pipeline, each with its own measuring module and output format:

    jukebox.pages.svs<id>   one movie / still image per page    svs<id>_frames.csv + svs<id>_arrays.npz
    jukebox.frames          SVS 5196 CO2, four camera moves     svs5196_<move>_frames.csv + svs5196_profiles.npz
    jukebox.nightlights_frames  SVS 5313 night lights           svs5313_eic_frames.csv + svs5313_eic_grids.npz
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from . import frames, nightlights_frames, pages, svs
from .paths import RAW_DIR


@dataclass(frozen=True)
class MeasuredPage:
    """One SVS page whose movies this project measures."""
    viz_id: int
    movies: dict[str, str]          # short name -> movie filename the scripts render with (first = default)
    downloads: dict[Path, str]      # raw file -> URL, downloaded when missing
    run: Callable[[], str]          # measure the raw files, write data/derived/, return a one-line summary
    outputs: tuple[Path, ...]       # what run() writes

    @property
    def movie(self) -> str:
        """The movie the preview renders with by default."""
        return next(iter(self.movies.values()))

    def resolve(self, movie: str | None) -> str:
        """A movie by short name ('zoom'), filename, or unique part of a filename; None -> the default."""
        if not movie:
            return self.movie
        if movie in self.movies:
            return self.movies[movie]
        if movie in self.movies.values():
            return movie
        found = [m for m in self.movies.values() if movie in m]
        if len(found) == 1:
            return found[0]
        raise ValueError(f"SVS {self.viz_id} has no single measured movie matching {movie!r}; "
                         f"use one of {', '.join(self.movies)}")


# ---- the three kinds of page --------------------------------------------------------------------------------

def _page(viz_id: int) -> MeasuredPage:
    mod = pages.module(viz_id)
    raw = pages.raw_path(viz_id)

    def run() -> str:
        table, arrays = mod.extract(raw)
        pages.save(viz_id, table, arrays)
        f = pages.load(viz_id, mod.MOVIE)
        return (f"{f.n_frames} {'scan steps' if f.still else 'frames'} -> {f.duration:.1f} s at {f.fps:g}/s, "
                f"{f.labels[0]!r} .. {f.labels[-1]!r}, arrays {sorted(f.arrays)}")

    downloads = {raw.with_name(name): url for name, url in {mod.MOVIE: mod.URL, **getattr(mod, "EXTRA", {})}.items()}
    return MeasuredPage(viz_id, {"movie": mod.MOVIE}, downloads, run,
                        (pages.table_path(viz_id), pages.arrays_path(viz_id)))


def _co2() -> MeasuredPage:
    raw = RAW_DIR / "svs5196"

    def run() -> str:
        profiles, parts = {}, []
        for tag, name in frames.MOVIES.items():
            table, profiles[tag] = frames.extract(raw / name, tag)
            table.to_csv(frames.path_for(5196, tag), index=False, lineterminator="\n")
            parts.append(f"{tag} {len(table)} frames (plume {table.plume.min():.2f}-{table.plume.max():.2f} %)")
        np.savez_compressed(frames.PROFILES_PATH, **profiles)
        return ", ".join(parts)

    return MeasuredPage(5196, dict(frames.MOVIES), {raw / n: frames.BASE_URL + n for n in frames.MOVIES.values()},
                        run, (*(frames.path_for(5196, t) for t in frames.MOVIES), frames.PROFILES_PATH))


def _nightlights() -> MeasuredPage:
    def run() -> str:
        table = nightlights_frames.extract(nightlights_frames.RAW_PATH)
        table.to_csv(nightlights_frames.FEATURES_PATH, index=False, lineterminator="\n")
        grids = nightlights_frames.extract_grids(nightlights_frames.RAW_PATH)
        np.savez_compressed(nightlights_frames.GRIDS_PATH, **grids)
        return f"{len(table)} frames, {len(grids)} grids"

    return MeasuredPage(5313, {"eic": nightlights_frames.MOVIE},
                        {nightlights_frames.RAW_PATH: nightlights_frames.URL}, run,
                        (nightlights_frames.FEATURES_PATH, nightlights_frames.GRIDS_PATH))


def registry() -> dict[int, MeasuredPage]:
    """Every measured page, by SVS id."""
    out = {5196: _co2(), 5313: _nightlights()}
    out.update({viz_id: _page(viz_id) for viz_id in pages.PAGES})
    return out


def page(viz_id: int) -> MeasuredPage | None:
    """The measured page with this id, or None if the project does not measure it."""
    return registry().get(int(viz_id))


# ---- command line -------------------------------------------------------------------------------------------

def measure(entry: MeasuredPage, download: Callable[[str, Path], Path] = svs.download_file) -> str:
    """Download what is missing, then measure: returns run()'s summary."""
    for path, url in entry.downloads.items():
        if not path.exists():
            print(f"SVS {entry.viz_id}: downloading {path.name} ...", flush=True)
            download(url, path)
    return entry.run()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m jukebox.measure", description=__doc__.split("\n\n")[0])
    ap.add_argument("ids", nargs="*", type=int, help="SVS page ids (default: every measured page)")
    ap.add_argument("--list", action="store_true", help="show what each page downloads and writes, then stop")
    args = ap.parse_args(argv)
    known = registry()
    if unknown := [i for i in args.ids if i not in known]:
        ap.error(f"not a measured page: {unknown}; measured pages: {', '.join(map(str, known))}")
    for viz_id in args.ids or list(known):
        entry = known[viz_id]
        if args.list:
            have = sum(p.exists() for p in entry.downloads)
            print(f"SVS {viz_id}: {have}/{len(entry.downloads)} raw files present -> "
                  + ", ".join(p.name for p in entry.outputs))
            continue
        t0 = time.perf_counter()
        summary = measure(entry)
        print(f"SVS {viz_id}: {summary} ({time.perf_counter() - t0:.0f} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
