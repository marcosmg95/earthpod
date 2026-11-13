"""PoC 5 — Black Marble night lights per region and year (data behind SVS 5313).

Reads backend/data/raw/blackmarble/VNP46A4.*.h5 (run data/download_blackmarble.ps1 first) and writes
backend/data/derived/blackmarble_annual.csv and .json: for each region whose tile is present,
mean / median / summed radiance (nW/cm^2/sr) per year plus % change vs the first year.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jukebox import blackmarble as bm  # noqa: E402
from jukebox.data import DERIVED_DIR, RAW_DIR  # noqa: E402

SRC = RAW_DIR / "blackmarble"


def main():
    files = sorted(SRC.glob("VNP46A4.*.h5"))
    if not files:
        sys.exit(f"No VNP46A4 files in {SRC}. Run backend/data/download_blackmarble.ps1 first.")

    rows = []
    for path in files:
        year, tile = bm.parse_name(path)
        for region in bm.REGIONS.values():
            if region.tile == tile:
                rows.append(bm.region_stats(path, region))
                print(f"{region.key:10s} {year}  mean {rows[-1]['mean_radiance']:7.2f} nW/cm2/sr")

    out = {}
    for r in sorted(rows, key=lambda r: (r["region"], r["year"])):
        series = out.setdefault(r["region"], [])
        base = series[0]["sum_radiance"] if series else r["sum_radiance"]
        r["pct_change_vs_first"] = round(100.0 * (r["sum_radiance"] / base - 1.0), 2) if base else None
        series.append(r)

    DERIVED_DIR.mkdir(exist_ok=True)
    flat = [r for s in out.values() for r in s]
    csv_path = DERIVED_DIR / "blackmarble_annual.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0]))
        w.writeheader()
        w.writerows(flat)

    json_path = DERIVED_DIR / "blackmarble_annual.json"
    doc = {
        "source": "NASA Black Marble VNP46A4 v002 (LAADS DAAC), Suomi NPP VIIRS; visual: NASA SVS 5313",
        "units": "nW/cm^2/sr",
        "regions": {k: {"name": bm.REGIONS[k].name, "years": v} for k, v in out.items()},
    }
    json_path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"Wrote {csv_path}\nWrote {json_path}")


if __name__ == "__main__":
    main()
