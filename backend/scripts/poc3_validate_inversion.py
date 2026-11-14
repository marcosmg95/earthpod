"""PoC 3 — Validity check: NASA frame colours -> degC, compared with GISTEMP.

Needs data/raw/ from backend/data/download_data.ps1 (SVS 5450 movie, time.txt, colorbar).
Also writes one low-res frame per year to frontend/player/frames/ for the web player.

    uv run python scripts/poc3_validate_inversion.py
    uv run python scripts/poc3_validate_inversion.py --flip --max-de 15   # if r is negative / coverage low
"""
import argparse
import sys
from pathlib import Path


import cv2
import numpy as np
import pandas as pd

from jukebox import colormap, data

POC = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--movie", default=str(data.RAW_DIR / "svs5450_SOS_4096x2048.mp4"))
    ap.add_argument("--colorbar", default=str(data.RAW_DIR / "svs5450_cbar_1000px.png"))
    ap.add_argument("--flip", action="store_true", help="colorbar runs high->low")
    ap.add_argument("--max-de", type=float, default=12.0, help="max CIELAB distance to accept a pixel")
    ap.add_argument("--analysis-width", type=int, default=360)
    ap.add_argument("--web-width", type=int, default=960)
    a = ap.parse_args()

    years = data.load_frame_years()
    if years is None or not Path(a.movie).exists():
        sys.exit("Missing backend/data/raw files. Run backend/data/download_data.ps1 first.")
    lut, t = colormap.lut_from_colorbar(colormap.read_rgb(a.colorbar), flip=a.flip)
    glob = data.load_global_annual()

    frames_dir = POC.parent / "frontend" / "player" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(a.movie)
    rows = []
    for year in sorted(set(years)):
        idx = data.frame_for_year(years, year)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, bgr = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        web = cv2.resize(bgr, (a.web_width, a.web_width // 2), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(frames_dir / f"frame_{idx:03d}.png"), web)
        small = cv2.resize(rgb, (a.analysis_width, a.analysis_width // 2), interpolation=cv2.INTER_AREA)
        field = colormap.invert(small, lut, t, a.max_de)
        rows.append(dict(Year=year, frame=idx, t_mean=colormap.area_mean(field),
                         coverage=colormap.coverage(field), gistemp=glob.get(year, np.nan)))
        print(f"{year} frame {idx:3d}  t={rows[-1]['t_mean']:.3f}  coverage={rows[-1]['coverage']:.0%}", end="\r")
    cap.release()

    df = pd.DataFrame(rows).set_index("Year")
    df["gistemp_5yr"] = glob.rolling(5, center=True, min_periods=3).mean().reindex(df.index)
    ok = df.dropna(subset=["t_mean", "gistemp"])
    r1 = ok["t_mean"].corr(ok["gistemp"])
    r5 = ok["t_mean"].corr(ok["gistemp_5yr"])
    slope, icpt = np.polyfit(ok["t_mean"], ok["gistemp"], 1)
    df["inverted_c"] = df["t_mean"] * slope + icpt

    out = data.DERIVED_DIR
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "validation_svs5450.csv")
    print(f"\nYears: {len(ok)} · mean coverage {ok['coverage'].mean():.0%}")
    print(f"r vs GISTEMP annual = {r1:.3f}   r vs 5-yr mean = {r5:.3f}")
    print(f"Implied colorbar range: {icpt:+.2f} .. {slope + icpt:+.2f} degC")
    if r1 < 0:
        print("Negative r: try --flip")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)
    ax.plot(ok.index, ok["gistemp"], color="#B4531E", lw=2, label="NASA GISTEMP v4 (measured)")
    ax.plot(ok.index, ok["inverted_c"], color="#10202B", lw=1.5, ls="--",
            label="Read back from SVS 5450 frame colours")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("Anomaly vs 1951–1980 (°C)")
    ax.set_title(f"Frame colours vs measured data: r = {r1:.3f}")
    ax.legend(frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "validation_svs5450.png")
    print(f"Wrote {out / 'validation_svs5450.csv'} and .png; frames in {frames_dir}")


if __name__ == "__main__":
    main()
