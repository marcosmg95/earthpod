"""Measure NASA SVS 5313's EIC movie for the night-lights sonification.

Download it with data/download_data.ps1, then run:
    uv run python scripts/poc7_svs5313_features.py
"""
import numpy as np

from jukebox import data, nightlights_frames


def main():
    movie = data.RAW_DIR / "svs5313_EIC_2160p30_h265.mp4"
    table = nightlights_frames.extract(movie)
    table.to_csv(nightlights_frames.FEATURES_PATH, index=False, lineterminator="\n")
    print(f"{len(table)} frames -> {nightlights_frames.FEATURES_PATH}")
    grids = nightlights_frames.extract_grids(movie)
    np.savez_compressed(nightlights_frames.GRIDS_PATH, **grids)
    print(f"{len(grids)} grids -> {nightlights_frames.GRIDS_PATH}")


if __name__ == "__main__":
    main()
