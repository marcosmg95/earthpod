"""PoC 8 — measure the movies / images of the challenge's SVS pages for the sonification scripts.

Downloads each page's movie into data/raw/svs<id>/ (gitignored; resumes broken downloads) if missing, runs its
measuring module (jukebox/pages/svs<id>.py) and writes data/derived/svs<id>_frames.csv + svs<id>_arrays.npz
(committed: the explorer and the scripts need no download).

    uv run python scripts/poc8_page_features.py            # every page
    uv run python scripts/poc8_page_features.py 5669 4950  # some pages
"""
import sys
import time

import requests

from jukebox import pages


def download(url: str, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    for attempt in range(30):
        have = part.stat().st_size if part.exists() else 0
        try:
            with requests.get(url, stream=True, timeout=120, headers={"Range": f"bytes={have}-"} if have else {}) as r:
                if r.status_code == 416:          # already complete
                    break
                r.raise_for_status()
                with open(part, "ab" if have and r.status_code == 206 else "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            break
        except requests.RequestException as e:
            print(f"  download interrupted ({type(e).__name__}), resuming ({attempt + 1})")
            time.sleep(2)
    else:
        raise RuntimeError(f"Could not download {url}")
    part.rename(path)


def main(ids: list[int]) -> None:
    for viz_id in ids:
        mod = pages.module(viz_id)
        path = pages.raw_path(viz_id)
        for name, url in {mod.MOVIE: mod.URL, **getattr(mod, "EXTRA", {})}.items():
            if not path.with_name(name).exists():
                print(f"SVS {viz_id}: downloading {name} ...")
                download(url, path.with_name(name))
        t0 = time.perf_counter()
        table, arrays = mod.extract(path)
        pages.save(viz_id, table, arrays)
        f = pages.load(viz_id, mod.MOVIE)
        print(f"SVS {viz_id}: {f.n_frames} {'scan steps' if f.still else 'frames'} -> {f.duration:.1f} s at "
              f"{f.fps:g}/s, {f.labels[0]!r} .. {f.labels[-1]!r}, arrays {sorted(f.arrays)} "
              f"({time.perf_counter() - t0:.0f} s) -> {pages.table_path(viz_id).name}")


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or list(pages.PAGES))
