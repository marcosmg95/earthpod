"""Download the curated Earth image set for the arcade jukebox.

Sources (all public domain, no API key):
  * NASA Image and Video Library  https://images-api.nasa.gov  (one search per theme)
  * EPIC / DSCOVR full-disk Earth  https://epic.gsfc.nasa.gov
  * SVS 5450 temperature-anomaly frames already in frontend/player/frames (if present)

Writes frontend/arcade/images/*.jpg (max 1280 px) and frontend/arcade/images/manifest.json.

    python backend/scripts/fetch_arcade_images.py            # default set
    python backend/scripts/fetch_arcade_images.py --per-theme 2
"""
from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "frontend" / "arcade" / "images"
UA = {"User-Agent": "earth-jukebox-poc/0.1"}
MAX_SIDE = 1280

# (search query, short place/label shown on the title card). Chosen for colour variety,
# so each track sounds clearly different: blue ocean, red desert, white ice, black night...
THEMES = [
    ("hurricane from space station", "Hurricane"),
    ("Sahara desert from space", "Sahara"),
    ("aurora from space station", "Aurora"),
    ("city lights at night from space station", "City lights"),
    ("wildfire smoke satellite", "Wildfire"),
    ("glacier Landsat", "Glacier"),
    ("Amazon river from space", "Amazon"),
    ("Great Barrier Reef from space", "Coral reef"),
    ("Himalaya from space station", "Himalaya"),
    ("phytoplankton bloom", "Plankton bloom"),
    ("Antarctica ice shelf", "Antarctica"),
    ("volcano eruption from space", "Volcano"),
    ("Bahamas from space", "Bahamas"),
    ("Earth sunrise space station", "Sunrise"),
    ("Namib desert Landsat", "Namib"),
    ("Mediterranean Sea from space", "Mediterranean"),
]
EXCLUDE_IDS = {'PIA10088', 'iss069e004822'}  # hand-reviewed: off-theme or framed maps
SKIP_WORDS = re.compile(r"astronaut|crew|portrait|spacesuit|spacewalk|launch|rocket|diagram|chart|graph|logo|poster|spartan|shuttle|ISS\)|cygnus|freighter|canadarm", re.I)


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(text: str | None, limit: int = 220) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text.replace("�", "'")).strip()
    if len(text) > limit:
        cut = text[:limit]
        text = (cut[: cut.rfind(". ") + 1] if ". " in cut else cut.rsplit(" ", 1)[0] + "…")
    return text


def save_jpg(raw: bytes, path: Path) -> tuple[int, int]:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    im.save(path, "JPEG", quality=85, optimize=True)
    return im.size


def from_image_library(per_theme: int) -> list[dict]:
    out, seen = [], set()
    for query, label in THEMES:
        url = "https://images-api.nasa.gov/search?" + urllib.parse.urlencode(
            {"q": query, "media_type": "image", "page_size": 20})
        try:
            items = json.loads(get(url))["collection"]["items"]
        except Exception as e:  # network hiccup: keep going
            print(f"  ! search failed for {query!r}: {e}", file=sys.stderr)
            continue
        taken = 0
        for it in items:
            m = it["data"][0]
            nid, title = m.get("nasa_id"), m.get("title", "")
            if nid in seen or nid in EXCLUDE_IDS or SKIP_WORDS.search(title + " " + " ".join(m.get("keywords", []))):
                continue
            href = next((l["href"] for l in it.get("links", []) if "~medium" in l["href"]), None) \
                or next((l["href"] for l in it.get("links", []) if l.get("render") == "image"), None)
            if not href:
                continue
            fname = re.sub(r"[^A-Za-z0-9_-]", "_", nid) + ".jpg"
            try:
                w, h = save_jpg(get(href.replace(" ", "%20")), OUT / fname)
            except Exception as e:
                print(f"  ! download failed {nid}: {e}", file=sys.stderr)
                continue
            if w < 400 or h < 200:
                (OUT / fname).unlink(missing_ok=True)
                continue
            seen.add(nid)
            credit = "NASA" + (f" {m['center']}" if m.get("center") else "")
            if m.get("photographer"):
                credit += f" / {clean(m['photographer'], 60)}"
            if re.fullmatch(r"[A-Za-z0-9_-]+", title) or title.lower() == "earth observation":
                title = f"{label} seen from orbit"  # raw photo IDs make poor titles
            out.append({
                "id": nid, "file": fname, "title": clean(title, 60), "place": label,
                "date": (m.get("date_created") or "")[:10], "credit": credit,
                "source_url": f"https://images.nasa.gov/details/{urllib.parse.quote(nid)}",
                "alt": clean(m.get("description") or title),
            })
            print(f"  + {label:<15} {title[:60]}")
            taken += 1
            if taken >= per_theme:
                break
    return out


def from_epic(n: int = 3) -> list[dict]:
    try:
        days = json.loads(get("https://epic.gsfc.nasa.gov/api/natural"))
    except Exception as e:
        print(f"  ! EPIC failed: {e}", file=sys.stderr)
        return []
    out = []
    step = max(1, len(days) // n)
    for d in days[::step][:n]:
        date = d["date"][:10]
        y, mo, da = date.split("-")
        url = f"https://epic.gsfc.nasa.gov/archive/natural/{y}/{mo}/{da}/jpg/{d['image']}.jpg"
        fname = d["image"] + ".jpg"
        try:
            save_jpg(get(url), OUT / fname)
        except Exception as e:
            print(f"  ! EPIC download failed: {e}", file=sys.stderr)
            continue
        lat, lon = d["centroid_coordinates"]["lat"], d["centroid_coordinates"]["lon"]
        out.append({
            "id": d["image"], "file": fname, "title": "The whole Earth from a million miles away",
            "place": "Whole Earth", "date": date,
            "credit": "NASA EPIC team / NOAA DSCOVR", "source_url": "https://epic.gsfc.nasa.gov",
            "alt": f"The sunlit side of Earth seen from the DSCOVR spacecraft on {date}, centred near "
                   f"latitude {lat:.0f}, longitude {lon:.0f}.",
        })
        print(f"  + EPIC            {date}")
    return out


def from_svs_frames(n: int = 3) -> list[dict]:
    frames = sorted((ROOT.parent / "frontend" / "player" / "frames").glob("frame_*.png"))
    if not frames:
        return []
    sys.path.insert(0, str(ROOT))
    try:
        from jukebox.data import load_frame_years
        years = load_frame_years()
    except Exception:
        years = None
    pick = [frames[int(i * (len(frames) - 1) / (n - 1))] for i in range(n)]
    out = []
    for f in pick:
        idx = int(f.stem.split("_")[1])
        year = years[idx] if years and idx < len(years) else None
        fname = f"svs5450_{f.stem}.jpg"
        save_jpg(f.read_bytes(), OUT / fname)
        when = str(year) if year else ""
        out.append({
            "id": fname[:-4], "file": fname, "title": "Global temperature anomaly", "place": f"Temperature map {when}".strip(),
            "date": when, "credit": "NASA Scientific Visualization Studio (SVS 5450), GISTEMP v4",
            "source_url": "https://svs.gsfc.nasa.gov/5450",
            "alt": f"World map of surface temperature compared with 1951–1980{' in ' + when if when else ''}: "
                   "blue is cooler, red is warmer.",
        })
        print(f"  + SVS 5450        {when}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-theme", type=int, default=2)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print("NASA Image and Video Library:")
    items = from_image_library(args.per_theme)
    print("EPIC:")
    items += from_epic()
    print("SVS 5450 frames:")
    items += from_svs_frames()
    (OUT / "manifest.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(items)} images -> {OUT / 'manifest.json'}")


if __name__ == "__main__":
    main()
