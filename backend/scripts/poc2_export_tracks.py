"""PoC 2 — Export tracks.json for the accessible web player (frontend/player/index.html).

Writes frontend/player/tracks.json with, per year: values, MIDI notes per voice, record flag,
a screen-reader description, and (if data/raw/svs5450_time.txt exists) the movie
frame index. If data/derived/barcelona_annual.csv exists (PoC 4), adds a
'barcelona' track.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jukebox import data, mapping  # noqa: E402

WEB = Path(__file__).resolve().parents[2] / "frontend" / "player"


def track(df, voices, name):
    notes, info, dur = mapping.build_score(df, voices)
    d = mapping.score_to_dict(notes, info, dur, voices)
    d["name"] = name
    return d


def main():
    df = data.load_zonal_annual()[list(data.ZONES)]
    df["global"] = data.load_global_annual()
    out = {"source": "NASA GISTEMP v4 (GISTEMP Team, 2026); frames: NASA SVS 5450",
           "tracks": {"planet": track(df, mapping.DEFAULT_VOICES, "Planet")}}

    bcn = data.load_barcelona_annual()
    if bcn is not None:
        b = df.copy()
        b["barcelona"] = bcn
        voices = [mapping.DEFAULT_VOICES[0],
                  mapping.Voice("Barcelona", "barcelona", 0.25, mapping.TONIC_MIDI, 0.0,
                                "string", 0.6, 0.3)]
        b = b.dropna(subset=["barcelona"])
        out["tracks"]["barcelona"] = track(b, voices, "Barcelona region")

    frames = data.load_frame_years()  # SVS 5450 frames: temperature tracks only
    for t in out["tracks"].values():
        for y in t["years"]:
            y["frame"] = data.frame_for_year(frames, y["year"]) if frames else None

    night = data.load_blackmarble_annual()  # PoC 5: NASA Black Marble night lights
    if night is not None:
        out["tracks"]["night"] = mapping.build_night_track(night)
        out["source"] += "; night lights: NASA Black Marble VNP46A4 (SVS 5313)"

    if night is not None and bcn is not None:  # layers: only the years every dataset covers
        temp = df[["global"]].assign(barcelona=bcn)
        layers = mapping.build_layers_track(temp, night)
        for y in layers["years"]:
            y["frame"] = data.frame_for_year(frames, y["year"]) if frames else None
        out["tracks"]["layers"] = layers

    WEB.mkdir(exist_ok=True)
    path = WEB / "tracks.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, t in out["tracks"].items():
        print(f"{k}: {len(t['years'])} years, {t['duration_s']:.0f} s")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
