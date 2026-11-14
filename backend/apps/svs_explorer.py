"""SVS explorer: type a NASA SVS visualization id, see its metadata, media and linked pages.

    cd backend
    uv run python -m streamlit run apps/svs_explorer.py

The id is kept in the URL (?id=5450), so a page can be shared or bookmarked.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from jukebox import sonify, svs, synth
from sync_player import sync_player  # apps/ is on sys.path when Streamlit runs this file

SONIFICATIONS = Path(__file__).resolve().parents[1] / "sonifications"

# SVS pages the project already uses (handy starting points).
KNOWN = {
    5450: "GISTEMP temperature anomalies (Science On a Sphere)",
    5313: "Black Marble night lights",
    5196: "DYAMOND global CO2",
}
GALLERY_MAX = 12

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
    scripts = sonify.discover(SONIFICATIONS)
    if not movie_items:
        st.info("No movies on this page to sonify.")
    elif not scripts:
        st.info(f"No sonification scripts in {SONIFICATIONS}.")
    else:
        names = [m.filename for m in movie_items]
        movie = movie_items[names.index(st.selectbox("Movie", names, key=f"son_movie_{viz_id}"))]

        # 1. timeline: which data label is on screen at each video time
        tt = load_time_txt(viz_id)
        c1, c2 = st.columns([1, 3])
        fps = c1.number_input("Frames per second", min_value=1.0, max_value=120.0, step=1.0,
                              value=svs.fps_from_frames(items) or 30.0, key=f"son_fps_{viz_id}",
                              help="From the frame-folder name (…_30p) when available.")
        if tt:
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
        name = st.selectbox("Sonification script", list(scripts), key="son_script",
                            help=f"Python files in {SONIFICATIONS.name}/ — edit one, then press Render again.")
        path = scripts[name]
        try:
            mod = sonify.load(path)
            st.markdown(f"**{getattr(mod, 'TITLE', name)}** — {getattr(mod, 'DESCRIPTION', '')}")
        except Exception as e:  # show script errors instead of crashing the explorer
            st.exception(e)
            mod = None

        # 3. render + locked player
        key = (viz_id, movie.url, name, path.stat().st_mtime, fps,
               len(timeline.labels), timeline.labels[0], timeline.labels[-1])
        if timeline.duration > sonify.MAX_DURATION_S:
            st.warning(f"Timeline is {timeline.duration:.0f} s; the player handles up to "
                       f"{sonify.MAX_DURATION_S:.0f} s. Raise the fps or shorten the year range.")
        elif mod and st.button("Render sonification", type="primary"):
            ctx = sonify.SonifyContext(viz_id=viz_id, timeline=timeline, data=data)
            try:
                with st.spinner(f"Running {path.name}…"):
                    wav = synth.wav_bytes(sonify.run(path, ctx), ctx.sr)
                st.session_state.son = {"key": key, "wav": wav, "spans": timeline.spans(),
                                        "secs": timeline.duration}
            except Exception as e:
                st.exception(e)

        son = st.session_state.get("son")
        if son and son["key"] == key:
            aspect = movie.width / movie.height if movie.width and movie.height else 16 / 9
            sync_player(movie.url, son["wav"], son["spans"], son["secs"], aspect=aspect)
            st.download_button("Download sonification (.wav)", son["wav"], f"svs{viz_id}_{name}.wav",
                               mime="audio/wav")
            st.caption("Press play on the video: pause, seek and speed changes carry the audio with it.")
        elif son and son["key"][:2] == key[:2]:
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
