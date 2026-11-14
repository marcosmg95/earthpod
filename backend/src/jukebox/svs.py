"""NASA Scientific Visualization Studio (SVS) API client: https://svs.gsfc.nasa.gov/api/<id>.

Used by apps/svs_explorer.py to browse visualizations quickly, and reusable from scripts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests

API = "https://svs.gsfc.nasa.gov/api/{viz_id}"
PAGE = "https://svs.gsfc.nasa.gov/{viz_id}"
TIMEOUT = 30


@dataclass(frozen=True)
class MediaItem:
    group: str          # media group title (or widget name if untitled)
    media_type: str     # SVS media_type: Image, Movie, Frames, HyperwallShow, ...
    url: str
    filename: str
    ext: str            # lowercase extension without dot ("" for frame folders)
    width: int | None
    height: int | None
    alt_text: str


def fetch(viz_id: int, session: requests.Session | None = None) -> dict:
    """Raw JSON for one SVS page. Raises requests.HTTPError for unknown ids."""
    r = (session or requests).get(API.format(viz_id=viz_id), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def download_media(url: str) -> bytes:
    """Download an SVS media file. Raises requests.RequestException on failure."""
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    return r.content


def https_url(url: str) -> str:
    # The API returns http:// links; browsers block those as mixed content.
    return "https://" + url[len("http://"):] if url.startswith("http://") else url


def media_items(data: dict) -> list[MediaItem]:
    """Flatten media_groups -> items -> instance into a list (skips text-only items)."""
    out: list[MediaItem] = []
    for g in data.get("media_groups") or []:
        group = g.get("title") or g.get("widget") or ""
        for item in g.get("items") or []:
            inst = item.get("instance") or {}
            url = inst.get("url")
            if not url:
                continue
            name = inst.get("filename") or PurePosixPath(urlparse(url).path).name
            suffix = PurePosixPath(name).suffix.lower()
            # Frame folders have names like "foo_pngs" (no real extension).
            ext = suffix[1:] if 1 < len(suffix) <= 6 else ""
            out.append(MediaItem(
                group=group,
                media_type=inst.get("media_type") or item.get("type") or "",
                url=https_url(url),
                filename=name,
                ext=ext,
                width=inst.get("width"),
                height=inst.get("height"),
                alt_text=inst.get("alt_text") or "",
            ))
    return out


def credits_text(data: dict) -> str:
    """'Role: Name (Employer), ...; Role: ...' for captions."""
    parts = []
    for c in data.get("credits") or []:
        people = ", ".join(
            p["name"] + (f" ({p['employer']})" if p.get("employer") else "")
            for p in c.get("people") or []
        )
        parts.append(f"{c.get('role', '')}: {people}")
    return "; ".join(parts)


def linked_pages(data: dict) -> list[dict]:
    """Related/recommended/version pages as {id, title, page_type, relation}."""
    rels = ["related", "recommended_pages", "products", "sources",
            "newer_versions", "older_versions", "alternate_versions"]
    out = []
    for rel in rels:
        for p in data.get(rel) or []:
            if isinstance(p, dict) and p.get("id"):
                out.append({"id": p["id"], "title": p.get("title", ""),
                            "page_type": p.get("page_type", ""), "relation": rel})
    return out


# ---- timeline helpers (video time <-> data) --------------------------------

def vis_dirs(data: dict) -> list[str]:
    """Unique /vis/ directories that hold this page's media (where time.txt lives)."""
    dirs: list[str] = []
    for it in media_items(data):
        u = urlparse(it.url)
        if "/frames/" in u.path:   # .../a005450/frames/3840x2160_16x9_30p/ -> .../a005450/
            path = u.path.split("/frames/")[0]
        else:                      # file or folder: its parent directory
            path = u.path.rstrip("/").rsplit("/", 1)[0]
        d = f"{u.scheme}://{u.netloc}{path}/"
        if d not in dirs:
            dirs.append(d)
    return dirs


def fetch_time_txt(data: dict, session: requests.Session | None = None) -> tuple[str, list[str]] | None:
    """(url, labels) from the first <vis dir>/time.txt that exists: one label per movie frame."""
    for d in vis_dirs(data):
        url = d + "time.txt"
        try:
            r = (session or requests).get(url, timeout=TIMEOUT)
        except requests.RequestException:
            continue
        if r.ok and "html" not in r.headers.get("content-type", ""):
            labels = [x.strip() for x in r.text.splitlines() if x.strip()]
            if labels:
                return url, labels
    return None


def fps_from_frames(items: list[MediaItem]) -> float | None:
    """Frame rate from SVS frame-folder names like '3840x2160_16x9_30p' (-> 30)."""
    for it in items:
        if it.media_type == "Frames":
            m = re.search(r"_(\d{2,3})p\b", it.filename)
            if m:
                return float(m.group(1))
    return None
