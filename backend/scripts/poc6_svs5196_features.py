"""PoC 6 — measure the SVS 5196 (DYAMOND global CO2) movies frame by frame for the sonification scripts.

Downloads the 1080p movies into data/raw/svs5196/ (gitignored, ~120 MB) if missing, then writes
data/derived/svs5196_<move>_frames.csv and svs5196_profiles.npz (committed; see jukebox/frames.py).

    uv run python scripts/poc6_svs5196_features.py
"""
import numpy as np
import requests

from jukebox import data, frames

BASE = "https://svs.gsfc.nasa.gov/vis/a000000/a005100/a005196/"
MOVIES = {
    "orbit": "dyamondPointCloud_12-1-2023b_dyamond_co2_anim_globe_orbit_1080p30_h265.mp4",
    "zoom": "dyamondPointCloud_3-29-2023a_dyamond_co2_anim_globe_zoom_1080p30.mp4",
    "zoomwest": "dyamondPointCloud_1-22-2025a_dyamond_co2_anim_globe_zoomwest_3x3hyperwall_1080p30_2.mp4",
    "tilt": "dyamondPointCloud_12-4-2023b_dyamond_co2_anim_globe_tilt_1080p30.mp4",
}


def main():
    raw = data.RAW_DIR / "svs5196"
    raw.mkdir(parents=True, exist_ok=True)
    profiles = {}
    for tag, name in MOVIES.items():
        assert frames.movie_tag(name) == tag, name
        path = raw / name
        if not path.exists():
            print(f"downloading {name} ...")
            r = requests.get(BASE + name, timeout=300)
            r.raise_for_status()
            path.write_bytes(r.content)
        table, profiles[tag] = frames.extract(path, tag)
        out = frames.path_for(5196, tag)
        table.to_csv(out, index=False, lineterminator="\n")
        print(f"{tag:9s} {len(table)} frames  plume {table.plume.min():.2f}-{table.plume.max():.2f} %  "
              f"{table.label.iloc[0]} .. {table.label.iloc[-1]}  -> {out.name}")
    np.savez_compressed(data.DERIVED_DIR / "svs5196_profiles.npz", **profiles)


if __name__ == "__main__":
    main()
