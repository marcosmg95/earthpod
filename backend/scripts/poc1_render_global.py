"""PoC 1 — Render the 'warming planet' track from real GISTEMP numbers to a WAV.

    python backend/scripts/poc1_render_global.py                  # 1880-2025, all voices
    python backend/scripts/poc1_render_global.py --lead-only      # just the global melody
    python backend/scripts/poc1_render_global.py --years 1950 2025
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from jukebox import data, mapping, synth  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs=2, type=int)
    ap.add_argument("--lead-only", action="store_true")
    ap.add_argument("--out", default=str(OUT / "earth_jukebox_global.wav"))
    a = ap.parse_args()

    df = data.load_zonal_annual()[list(data.ZONES)]
    df["global"] = data.load_global_annual()
    voices = mapping.DEFAULT_VOICES[:1] if a.lead_only else mapping.DEFAULT_VOICES
    notes, info, dur = mapping.build_score(df, voices, tuple(a.years) if a.years else None)
    wav = synth.write_wav(a.out, synth.render(notes, dur))

    records = [y.year for y in info if y.record]
    print(f"Wrote {wav}  ({dur:.0f} s, {len(info)} years, {len(notes)} notes)")
    print(f"Record years (bell): {records}")
    print(f"Mapping: {mapping.MAPPING_TEXT}")


if __name__ == "__main__":
    main()
