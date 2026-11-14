"""SVS explorer: type a NASA SVS visualization id, see its metadata, media and linked pages.

    cd backend
    uv run python -m streamlit run apps/svs_explorer.py

The id is kept in the URL (?id=5450), so a page can be shared or bookmarked.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from jukebox import pages, sonify, svs, video
import live_player  # apps/ is on sys.path when Streamlit runs this file

SONIFICATIONS = Path(__file__).resolve().parents[1] / "sonifications"

# SVS pages the project already uses (handy starting points).
KNOWN = {
    5313: "Black Marble night lights",
    5196: "DYAMOND global CO2",
    5669: "GEOS aerosols (still map)",
    5533: "Air quality model runs",
    5011: "Lightning from the ISS",
    3912: "Sea surface currents and temperature",
    5425: "Perpetual Ocean 2",
    4960: "Atmospheric river",
    4950: "GEDI forest height",
}
GALLERY_MAX = 12
CACHE_RENDERS = 6   # recent renders kept, so going back to a setting you tried is instant

st.set_page_config(page_title="SVS explorer", page_icon="🛰️", layout="wide")


@st.cache_data(ttl=3600, show_spinner="Fetching from svs.gsfc.nasa.gov…")
def load(viz_id: int) -> dict:
    return svs.fetch(viz_id)


@st.cache_data(ttl=3600, show_spinner="Looking for time.txt…")
def load_time_txt(viz_id: int) -> tuple[str, list[str]] | None:
    return svs.fetch_time_txt(load(viz_id))


def go(viz_id: int) -> None:
    st.session_state.viz_id = int(viz_id)


# ---- choose an id -----------------------------------------------------------
if "viz_id" not in st.session_state:
    try:
        st.session_state.viz_id = int(st.query_params.get("id", 5450))
    except ValueError:
        st.session_state.viz_id = 5450

with st.sidebar:
    st.number_input("SVS visualization id", min_value=1, step=1, key="viz_id",
                    help="The number in svs.gsfc.nasa.gov/<id>. Use +/− to step through neighbours.")
    st.caption("Known in this project")
    for k, label in KNOWN.items():
        st.button(f"{k} · {label}", key=f"known_{k}", on_click=go, args=(k,),
                  width="stretch")
    hist = st.session_state.setdefault("history", [])
    if hist:
        st.caption("Recently viewed")
        for k, title in reversed(hist[-10:]):
            st.button(f"{k} · {title[:40]}", key=f"hist_{k}", on_click=go, args=(k,),
                      width="stretch")

viz_id = int(st.session_state.viz_id)
st.query_params["id"] = str(viz_id)

try:
    data = load(viz_id)
except requests.HTTPError as e:
    code = e.response.status_code if e.response is not None else "?"
    st.error(f"SVS returned HTTP {code} for id {viz_id}. Not every number is a page — try a neighbour.")
    st.stop()
except requests.RequestException as e:
    st.error(f"Could not reach the SVS API: {e}")
    st.stop()

title = data.get("title") or f"SVS {viz_id}"
if not hist or hist[-1][0] != viz_id:
    hist[:] = [h for h in hist if h[0] != viz_id] + [(viz_id, title)]

# ---- header -----------------------------------------------------------------
st.title(title)
st.markdown(
    f"[svs.gsfc.nasa.gov/{viz_id}]({svs.PAGE.format(viz_id=viz_id)}) · "
    f"{data.get('page_type', '')} · released {str(data.get('release_date', ''))[:10]} · "
    f"updated {str(data.get('update_date', ''))[:10]}"
)
cats = (data.get("nasa_science_categories") or []) + (data.get("keywords") or [])
if cats:
    st.caption(" · ".join(cats))

main = data.get("main_image") or {}
left, right = st.columns([2, 1])
with left:
    st.markdown(data.get("description") or "_No description._", unsafe_allow_html=True)
with right:
    if main.get("url"):
        st.image(svs.https_url(main["url"]), caption=main.get("alt_text") or None)

items = svs.media_items(data)
datasets = data.get("datasets") or []
linked = svs.linked_pages(data)

tab_media, tab_sonify, tab_data, tab_links, tab_raw = st.tabs([
    f"Media ({len(items)})", "Sonify", f"Datasets ({len(datasets)})",
    f"Linked pages ({len(linked)})", "Raw JSON",
])

# ---- media ------------------------------------------------------------------
with tab_media:
    if not items:
        st.info("No media on this page.")
    else:
        df = pd.DataFrame([i.__dict__ for i in items])
        c1, c2, c3 = st.columns([1, 1, 2])
        types = sorted(df.media_type.unique())
        exts = sorted(e for e in df.ext.unique() if e)
        sel_types = c1.multiselect("Media type", types, default=types)
        sel_exts = c2.multiselect("Extension", exts, default=exts,
                                  help="Frame folders have no extension and only show when this is empty.")
        q = c3.text_input("Filename contains", placeholder="e.g. 4k, print, colorbar")
        mask = df.media_type.isin(sel_types)
        if sel_exts:
            mask &= df.ext.isin(sel_exts)
        if q:
            mask &= df.filename.str.contains(q, case=False, regex=False)
        view = df[mask]

        st.dataframe(
            view[["media_type", "ext", "filename", "width", "height", "group", "url"]],
            column_config={"url": st.column_config.LinkColumn("url", display_text="open")},
            hide_index=True, width="stretch",
        )
        st.download_button("Download URL list (.txt)", "\n".join(view.url), f"svs{viz_id}_urls.txt")

        movies = view[view.ext.isin(["mp4", "webm", "mov"])]
        if not movies.empty:
            st.subheader("Preview a movie")
            pick = st.selectbox("Movie", movies.filename.tolist(), label_visibility="collapsed")
            st.video(movies.set_index("filename").loc[pick, "url"])

        images = view[view.ext.isin(["png", "jpg", "jpeg", "gif", "webp", "tif", "tiff"])]
        if not images.empty:
            st.subheader(f"Images ({len(images)}{', first ' + str(GALLERY_MAX) if len(images) > GALLERY_MAX else ''})")
            cols = st.columns(3)
            for n, row in enumerate(images.head(GALLERY_MAX).itertuples()):
                cols[n % 3].image(row.url, caption=row.filename, width="stretch")

# ---- sonify: data audio locked to a movie -----------------------------------
with tab_sonify:
    movie_items = [i for i in items if i.ext in ("mp4", "webm", "mov")]
    page_mod = pages.module(viz_id)
    if page_mod is not None:      # the measured movie first; a measured still image is played as a scan
        measured = [i for i in items if i.filename == page_mod.MOVIE]
        movie_items = measured[:1] + [i for i in movie_items if i.filename != page_mod.MOVIE]
    scripts = sonify.discover_for(SONIFICATIONS, viz_id)
    script_dir = sonify.folder_for(SONIFICATIONS, viz_id)
    if not movie_items:
        st.info("No movies on this page to sonify.")
    elif not scripts:
        st.info(f"No sonification scripts for SVS {viz_id} yet. Add one in "
                f"`sonifications/{script_dir.name}/` (template: `sonifications/svs5450/gistemp_lead.py`).")
    else:
        names = [m.filename for m in movie_items]
        movie = movie_items[names.index(st.selectbox("Movie", names, key=f"son_movie_{viz_id}"))]

        # 1. timeline: which data label is on screen at each video time
        c1, c2 = st.columns([1, 3])
        fps = c1.number_input("Frames per second", min_value=1.0, max_value=120.0, step=1.0,
                              value=svs.fps_from_frames(items) or sonify.DEFAULT_FPS, key=f"son_fps_{viz_id}",
                              help="From the frame-folder name (…_30p) when available.")
        measured = sonify.measured_timeline(viz_id, movie.filename, fps)   # committed measurements come first
        tt = None if measured else load_time_txt(viz_id)
        chapters = measured.chapters if measured else []
        is_still = bool(measured and measured.still)
        if measured:
            timeline = measured.timeline
            labels = timeline.labels
        if measured and measured.origin == "page":
            what = (f"a left-to-right scan of the image in {len(labels)} steps at {timeline.fps:g} per second"
                    if is_still else f"{len(labels)} frames at {timeline.fps:g} fps (the movie's own)")
            c2.markdown(f"**Timeline** from the measured movie (`scripts/poc8_page_features.py`): {what} → "
                        f"{timeline.duration:.1f} s, {labels[0]} … {labels[-1]}.")
        elif measured and measured.origin == "nightlights":
            c2.markdown(f"**Timeline** from the measured SVS 5313 movie: {len(labels)} frames "
                        f"→ {timeline.duration:.1f} s at {fps:g} fps (movie: 30 fps), in "
                        f"{len(chapters)} sections; year labels read from the movie.")
        elif measured:
            c2.markdown(f"**Timeline** from the movie's own frames (measured by `scripts/poc6_svs5196_features.py`): "
                        f"{len(labels)} frames, {labels[0]} … {labels[-1]} → {timeline.duration:.1f} s at {fps:g} fps")
        elif tt:
            tt_url, labels = tt
            timeline = sonify.Timeline(labels, fps)
            c2.markdown(f"**Timeline** from [time.txt]({tt_url}): {len(labels)} frames, "
                        f"{labels[0]} … {labels[-1]} → {timeline.duration:.1f} s at {fps:g} fps")
        else:
            c2.markdown("**Timeline:** this page has no time.txt, so years are spread evenly over the movie.")
            a, b, c = st.columns(3)
            y0 = a.number_input("First year", value=1880, step=1, key=f"son_y0_{viz_id}")
            y1 = b.number_input("Last year", value=2024, step=1, key=f"son_y1_{viz_id}")
            secs = c.number_input("Movie length (s)", min_value=1.0, value=30.0, step=1.0, key=f"son_len_{viz_id}")
            timeline = sonify.Timeline.linear(int(y0), int(y1), secs, fps)

        # 2. script
        name = st.selectbox("Sonification script", list(scripts), key=f"son_script_{viz_id}",
                            help=f"Python files in {SONIFICATIONS.name}/{script_dir.name}/ (plus generic ones in "
                                 f"{SONIFICATIONS.name}/) — edit one and it re-renders.")
        path = scripts[name]
        try:
            mod = sonify.load(path)
            st.markdown(f"**{getattr(mod, 'TITLE', name)}** — {getattr(mod, 'DESCRIPTION', '')}")
        except Exception as e:  # show script errors instead of crashing the explorer
            st.exception(e)
            mod = None

        # 2b. tunable constants the script lists in PARAMS (no code edit needed). Level constants of a stem
        # script (STEMS / OUTPUT_GAIN) are sliders in the player instead: the browser re-mixes them live.
        overrides = {}
        try:
            specs = sonify.params_of(mod) if mod else {}
        except AttributeError as e:
            st.error(str(e))
            specs = {}
        live = sonify.mix_params(mod) & set(specs) if mod else set()
        player_key = f"son_player_{viz_id}"
        mix_id = json.dumps([name, {k: specs[k].default for k in sorted(live)}])
        levels = st.session_state.get(player_key) or {}
        levels = {k: v for k, v in levels.items() if k in live} if levels.get("_mix") == mix_id else {}
        render_specs = {k: p for k, p in specs.items() if k not in live}
        if specs:
            with st.expander(f"Tune {len(specs)} parameters", expanded=True):
                if live:
                    st.caption(f"Layer levels ({', '.join(sorted(live))}) are live sliders under the video. "
                               "The sliders here re-render the audio (it swaps in without stopping the video).")
                cols = st.columns(min(max(len(render_specs), 1), 3))
                for n, (pname, p) in enumerate(render_specs.items()):
                    kind = int if isinstance(p.default, int) else float  # st.slider wants one number type
                    overrides[pname] = cols[n % len(cols)].slider(
                        pname, kind(p.lo), kind(p.hi), kind(p.default), kind(p.step),
                        key=f"son_param_{viz_id}_{name}_{pname}")
                changed = {k: v for k, v in {**overrides, **levels}.items() if v != specs[k].default}
                if changed:
                    st.caption("To keep these values, set them in the script:")
                    st.code("\n".join(f"{k} = {v:g}" for k, v in changed.items()), language="python")

        # 3. render (automatic, cached) + locked player
        key = (viz_id, movie.url, name, path.stat().st_mtime, fps,
               len(timeline.labels), timeline.labels[0], timeline.labels[-1], tuple(sorted(overrides.items())))
        cache = st.session_state.setdefault("son_cache", {})
        auto = st.toggle("Re-render automatically when a setting changes", value=True, key="son_auto",
                         help="About a second for the CO2 scripts. Turn off for slow scripts and use the button.")
        status = st.empty()
        if timeline.duration > sonify.MAX_DURATION_S:
            status.warning(f"Timeline is {timeline.duration:.0f} s; the player handles up to "
                           f"{sonify.MAX_DURATION_S:.0f} s. Raise the fps or shorten the year range.")
        elif mod and key not in cache and (auto or status.button("Render sonification", type="primary")):
            ctx = sonify.context_for(viz_id, timeline, movie.filename, data=data, params=overrides)
            try:
                status.caption(f"Rendering {path.name}…")
                stems = sonify.render_stems(path, ctx)
                cache[key] = {"wavs": live_player.stem_wavs(stems, ctx.sr), "meta": replace(stems, audio={}),
                              "spans": timeline.spans(), "secs": timeline.duration, "sr": ctx.sr,
                              "id": hashlib.sha1(repr(key).encode()).hexdigest()[:16]}
                while len(cache) > CACHE_RENDERS:          # each entry holds the stems as WAVs (~7 MB each)
                    cache.pop(next(iter(cache)))
                status.empty()
            except Exception as e:
                status.exception(e)

        son = cache.get(key)
        if son:
            meta = son["meta"]
            aspect = movie.width / movie.height if movie.width and movie.height else 16 / 9
            got = live_player.live_player(
                movie.url, son["wavs"], son["id"], live_player.mix_spec(meta, specs, levels), mix_id,
                meta.normalize, son["spans"], son["secs"], aspect=aspect, chapters=chapters,
                still=is_still, key=player_key)
            if got and got.get("_mix") == mix_id:
                levels = {k: v for k, v in got.items() if k in live}
            gains = {stem: levels.get(p, specs[p].default if p in specs else meta.gains[stem])
                     for stem, p in meta.params.items()}
            output = levels.get("OUTPUT_GAIN", meta.output)
            st.download_button("Download sonification (.wav)",
                               lambda: live_player.mix_wav(son["wavs"], gains, output, meta.normalize, son["sr"]),
                               f"svs{viz_id}_{name}.wav", mime="audio/wav",
                               help="The mix you hear, with the current levels.")
            video_key = (viz_id, movie.url)
            video_download = st.session_state.get("son_video_download")
            if video_download and video_download["key"] != video_key:
                del st.session_state["son_video_download"]
                video_download = None
            if not is_still and st.button(           # a still image has nothing to re-encode
"Prepare video-only download (H.264)", key=f"prepare_video_{viz_id}"):
                try:
                    with st.spinner("Downloading the movie from NASA SVS…"):
                        video_bytes = svs.download_media(movie.url)
                    with st.spinner("Re-encoding to H.264 MP4 (can take a minute for 4K movies)…"):
                        video_bytes = video.to_h264(video_bytes)
                except requests.RequestException as e:
                    st.error(f"Could not download the movie: {e}")
                except RuntimeError as e:
                    st.error(str(e))
                else:
                    video_download = {"key": video_key, "data": video_bytes}
                    st.session_state["son_video_download"] = video_download
            if video_download and video_download["key"] == video_key:
                st.download_button(
                    "Download video only (H.264 .mp4)",
                    video_download["data"],
                    video.h264_filename(movie.filename),
                    mime="video/mp4",
                    help=f"H.264 MP4, no audio, at most {video.MAX_WIDTH} px wide. The sonification is "
                         "not included; it remains available as a separate WAV.",
                )
            st.caption("Press play on the scan: the line shows where the sound is reading the image."
                       if is_still else
                       "Press play on the video: pause, seek and speed changes carry the audio with it.")
        elif not auto and mod:
            st.caption("Settings or script changed — press Render again.")

# ---- datasets ---------------------------------------------------------------
with tab_data:
    if datasets:
        st.dataframe(pd.DataFrame(datasets), hide_index=True, width="stretch")
    else:
        st.info("No datasets listed.")
    if data.get("credits"):
        st.markdown(f"**Credits:** {svs.credits_text(data)}")

# ---- linked pages -----------------------------------------------------------
with tab_links:
    if not linked:
        st.info("No linked pages.")
    for p in linked:
        a, b = st.columns([1, 5])
        a.button(f"Open {p['id']}", key=f"link_{p['relation']}_{p['id']}", on_click=go, args=(p["id"],))
        b.markdown(f"**{p['title']}** · {p['page_type']} · _{p['relation'].replace('_', ' ')}_")

# ---- raw --------------------------------------------------------------------
with tab_raw:
    raw = json.dumps(data, indent=2, ensure_ascii=False)
    st.download_button("Download JSON", raw, f"svs{viz_id}.json", mime="application/json")
    st.code(f"from jukebox import svs\ndata = svs.fetch({viz_id})\nitems = svs.media_items(data)", language="python")
    st.json(data, expanded=False)

st.caption("Data and media: NASA Scientific Visualization Studio. This tool is not endorsed by NASA.")
