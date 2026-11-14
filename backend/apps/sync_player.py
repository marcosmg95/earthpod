"""Video + sonification locked together: the <video> is the master clock, the <audio> follows it.

Play/pause/seek/speed on the video drive the audio; a drift check re-aligns it every frame.
No autoplay. Keyboard: the native video controls; Space on the focused video toggles play.
"""
from __future__ import annotations

import base64
import html as htmllib
import json

import streamlit as st

DRIFT_S = 0.08

_HTML = """
<style>
  :root { --fg:#1b1f24; --muted:#5b6470; --bg:#ffffff; --line:#d0d7de; }
  @media (prefers-color-scheme: dark) { :root { --fg:#e6edf3; --muted:#9aa4af; --bg:#0e1117; --line:#30363d; } }
  body { margin:0; font:14px/1.4 system-ui, sans-serif; color:var(--fg); background:var(--bg); }
  video { width:100%; max-height:__VH__px; background:#000; display:block; }
  .bar { display:flex; flex-wrap:wrap; gap:12px 20px; align-items:center; padding:8px 2px; }
  .label { font-size:22px; font-weight:600; min-width:7ch; font-variant-numeric:tabular-nums; }
  .muted { color:var(--muted); }
  .warn { color:#b35900; }
  .sr { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
  input[type=range] { vertical-align:middle; }
</style>
<video id="v" controls preload="metadata" playsinline src="__VIDEO__"
       aria-label="SVS movie; the data sonification plays in sync with it"></video>
<audio id="a" preload="auto" src="data:audio/wav;base64,__WAV__"></audio>
<div class="bar">
  <span class="label" id="lbl" aria-hidden="true">—</span>
  <label>Sonification volume
    <input id="vol" type="range" min="0" max="1" step="0.05" value="0.9"></label>
  <label><input id="mute" type="checkbox"> Mute sonification</label>
  <span class="muted" id="dur"></span>
</div>
<div class="sr" id="live" aria-live="polite"></div>
<script>
const v = document.getElementById('v'), a = document.getElementById('a');
const lbl = document.getElementById('lbl'), live = document.getElementById('live');
const spans = __SPANS__;            // [[label, t0, t1], ...]
const DRIFT = __DRIFT__, AUDIO_S = __AUDIO_S__;

function labelAt(t) {               // binary search over spans
  let lo = 0, hi = spans.length - 1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (t < spans[m][1]) hi = m - 1; else if (t >= spans[m][2]) lo = m + 1; else return spans[m][0];
  }
  return spans.length && t >= spans[spans.length - 1][2] ? spans[spans.length - 1][0] : '—';
}
function align() { if (Math.abs(a.currentTime - v.currentTime) > DRIFT) a.currentTime = Math.min(v.currentTime, AUDIO_S); }
function announce() { live.textContent = (v.paused ? 'Paused at ' : 'At ') + labelAt(v.currentTime); }

v.addEventListener('play',    () => { align(); a.playbackRate = v.playbackRate; a.play().catch(() => {}); });
v.addEventListener('playing', () => { align(); if (a.paused) a.play().catch(() => {}); });
v.addEventListener('waiting', () => a.pause());            // video buffering: hold the audio
v.addEventListener('pause',   () => { a.pause(); align(); announce(); });
v.addEventListener('ended',   () => a.pause());
v.addEventListener('seeking', () => { a.currentTime = Math.min(v.currentTime, AUDIO_S); });
v.addEventListener('seeked',  () => { align(); announce(); });
v.addEventListener('ratechange', () => { a.playbackRate = v.playbackRate; });
v.addEventListener('loadedmetadata', () => {
  const d = document.getElementById('dur'), diff = Math.abs(v.duration - AUDIO_S);
  d.textContent = `movie ${v.duration.toFixed(1)} s · audio ${AUDIO_S.toFixed(1)} s`;
  if (diff > 0.5) { d.className = 'warn'; d.textContent += ' — lengths differ: check the fps / timeline'; }
});
document.getElementById('vol').addEventListener('input', e => { a.volume = +e.target.value; });
document.getElementById('mute').addEventListener('change', e => { a.muted = e.target.checked; });
a.volume = 0.9;

let last = null;
(function tick() {
  if (!v.paused && !v.seeking) align();
  const l = labelAt(v.currentTime);
  if (l !== last) { lbl.textContent = l; last = l; }      // visual only; screen readers hear pause/seek
  requestAnimationFrame(tick);
})();
</script>
"""


def sync_player(video_url: str, wav: bytes, spans: list[tuple[str, float, float]], audio_s: float,
                aspect: float = 16 / 9, width_px: int = 900) -> None:
    """Render the locked player. `spans` = Timeline.spans(); `aspect` = movie width / height."""
    video_h = int(min(width_px / max(aspect, 0.3), 640))
    # URL and labels come from SVS (external): escape for the attribute / the <script> block.
    spans_js = json.dumps([[l, round(t0, 4), round(t1, 4)] for l, t0, t1 in spans]).replace("<", "\\u003c")
    page = (_HTML
            .replace("__VIDEO__", htmllib.escape(video_url, quote=True))
            .replace("__WAV__", base64.b64encode(wav).decode("ascii"))
            .replace("__SPANS__", spans_js)
            .replace("__DRIFT__", str(DRIFT_S))
            .replace("__AUDIO_S__", f"{audio_s:.4f}")
            .replace("__VH__", str(video_h)))
    st.iframe(page, height=video_h + 70)
