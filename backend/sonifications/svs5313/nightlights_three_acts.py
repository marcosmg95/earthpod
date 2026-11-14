"""NASA SVS 5313 night lights in three acts: years, change map, regional zooms.

Every act is a left-to-right scan of the map: pan = longitude, pitch = latitude (north is high),
loudness = how bright that spot is. The scans are measured from the movie's pictures
(nightlights_frames.extract_grids), so what you hear is what is on screen.
"""
import numpy as np

from jukebox import nightlights_frames as nf, synth

TITLE = "Night lights: three acts"
DESCRIPTION = (
    "Scans NASA SVS 5313's EIC movie (Black Marble night lights, 2012–2023) left to right, like a radar: "
    "pan is longitude, pitch is latitude (north high), loudness is brightness, notes on a pentatonic scale. "
    "1 · Years: each year the whole world is swept in 0.5 s with soft plucks; places that are brighter than "
    "in 2012 add a bell on top, so the sweep fills with bells as the lights spread. "
    "2 · Change map: three slow sweeps of the same picture, first purple ('new lights') as high bells, "
    "then orange ('lights out') as low plucks, then both together at their true balance. "
    "3 · Regional zooms: a tour of the four boxes, left to right Western Europe, Eastern Mediterranean, "
    "Ukraine, India, then each year all four are swept at once, each on its own side of the stereo field "
    "and louder where the region is brighter; the final change map is toured again, purple high, orange low. "
    "Picture indices, not radiance: colours, labels and zooms of the movie shape the sound.")

PENTATONIC = (0, 2, 4, 7, 9)
FLOOR = 0.04                      # cells dimmer than this share of the loud end stay silent
WORLD = dict(root=48, steps=15)   # C3 .. C6 (15 rows)
PURPLE = dict(root=72, steps=10, timbre="bell")    # new lights: high bells
ORANGE = dict(root=40, steps=10, timbre="pluck")   # lights out: low plucks
BOX_VOICE = {"weur": ("pluck", 48), "emed": ("soft", 55), "ukr": ("bell", 48), "ind": ("pluck", 55)}
MAX_BOOST = 8.0
_cache: dict = {}


def _midi(step: int, root: int) -> int:
    return root + 12 * (step // 5) + PENTATONIC[step % 5]


def _tone(midi: int, timbre: str, sr: int) -> np.ndarray:
    key = (midi, timbre, sr)
    if key not in _cache:
        hz = 440.0 * 2 ** ((midi - 69) / 12)
        _cache[key] = synth.tone(hz, 1.0 if timbre == "bell" else 0.45, timbre, sr)
    return _cache[key]


def _pool(grid: np.ndarray, cols: int) -> np.ndarray:
    """Max of each group of columns, so a thin bright city is not averaged away."""
    return np.stack([g.max(axis=1) for g in np.array_split(grid, cols, axis=1)], axis=1)


def _scale(*grids) -> float:
    """Loud end of a set of grids: their 99th percentile (1.0 if they are all dark)."""
    v = np.concatenate([np.ravel(g) for g in grids])
    v = v[v > 0]
    return float(np.percentile(v, 99)) if v.size else 1.0


def _sweep(out, grid, t0, width, scale, sr, *, pan=0.0, spread=1.0, gain=0.3, per_col=2,
           steps=None, root=48, timbre="pluck", octave=0):
    """Play grid (rows north->south, cols west->east) from t0 over `width` s.

    Per column the brightest `per_col` rows sound: pitch from the row, pan from the column.
    """
    rows, cols = grid.shape
    steps = steps or rows
    for c in range(cols):
        frac = (c + 0.5) / cols
        for r in np.argsort(grid[:, c])[::-1][:per_col]:
            level = grid[r, c] / scale
            if level < FLOOR:
                continue
            step = round((1 - r / max(rows - 1, 1)) * (steps - 1))
            y = _tone(_midi(step, root) + octave, timbre, sr) * gain * min(1.0, np.sqrt(level))
            synth.add_at(out, synth.pan_stereo(y, np.clip(pan + spread * (2 * frac - 1), -1, 1)),
                         t0 + frac * width, sr)


class _Sections:
    """Each section is mixed into its own buffer, then set to the same loudness (sparse ones need more gain)."""

    def __init__(self, n, sr):
        self.n, self.sr, self.items = n, sr, []

    def new(self, t0, t1, target=0.06):
        buf = np.zeros((self.n, 2))
        self.items.append((buf, int(t0 * self.sr), int(t1 * self.sr), target))
        return buf

    def mix(self):
        total = np.zeros((self.n, 2))
        for buf, i0, i1, target in self.items:
            rms = np.sqrt((buf[i0:i1] ** 2).mean())
            total += buf * (min(target / rms, MAX_BOOST) if rms > 1e-6 else 0.0)
        return synth.normalize(total)


def render(ctx):
    g = ctx.nightlights_grids()
    n, sr = ctx.n_samples, ctx.sr
    fps = nf.FPS
    sections = _Sections(n, sr)
    scenes = [s[0] / fps for s in nf.SCENES] + [n / sr]

    # ---- Act 1: a world sweep per year; brighter-than-2012 places add bells ----------------
    world = np.stack([_pool(y, 32) for y in g["world_light"]])
    growth = np.clip(world - world[0], 0, None)
    scale = _scale(world)
    out = sections.new(scenes[0], scenes[1])
    growth_scale = _scale(growth)
    for year, (a, b) in enumerate(nf.year_windows("years")):
        t0, width = a / fps, 0.85 * (b - a) / fps
        _sweep(out, world[year], t0, width, scale, sr, gain=0.16, **WORLD)
        if year:
            _sweep(out, growth[year], t0, width, growth_scale, sr, gain=0.3, per_col=1,
                   root=WORLD["root"], steps=WORLD["steps"], timbre="bell", octave=12)

    # ---- Act 2: purple, then orange, then both (same picture, three readings) -------------
    purple, orange = _pool(g["world_purple"], 64), _pool(g["world_orange"], 64)
    start, end = (nf.SCENES[1][0] + 18) / fps, nf.SCENES[2][0] / fps
    slot = (end - start) / 3
    passes = [([(purple, PURPLE)], _scale(purple)), ([(orange, ORANGE)], _scale(orange)),
              ([(purple, PURPLE), (orange, ORANGE)], _scale(purple, orange))]  # last: one shared scale
    for i, (layers, scale_i) in enumerate(passes):
        out = sections.new(start + i * slot, start + (i + 1) * slot)
        for layer, voice in layers:
            _sweep(out, layer, start + i * slot, 0.9 * slot, scale_i, sr, gain=0.3, **voice)

    # ---- Act 3: tour of the four zoom boxes, then all four sweep every year ---------------
    box_light = np.stack([[_pool(y, 20) for y in b] for b in g["box_light"]])   # (box, year, rows, cols)
    box_scale = _scale(box_light)
    box_growth = np.clip(box_light - box_light[:, :1], 0, None)
    box_growth_scale = _scale(box_growth)
    tour_start, tour_end = nf.BOXES_IN[1] / fps, nf.year_windows("zoom_years")[1][0] / fps
    tour = (tour_end - tour_start) / len(nf.BOXES)
    tour_out = sections.new(tour_start, tour_end)
    out = sections.new(tour_end, scenes[3])
    for k, box in enumerate(nf.BOXES):
        timbre, root = BOX_VOICE[box.key]
        _sweep(tour_out, box_light[k, 0], tour_start + k * tour, 0.9 * tour, box_scale, sr, pan=box.pan, spread=0.15,
               gain=0.3, per_col=3, root=root, steps=12, timbre=timbre)
        for year, (a, b) in enumerate(nf.year_windows("zoom_years")):
            if year == 0:
                continue
            t0, width = a / fps, 0.85 * (b - a) / fps
            _sweep(out, box_light[k, year], t0, width, box_scale, sr, pan=box.pan, spread=0.15, gain=0.2,
                   root=root, steps=12, timbre=timbre)
            _sweep(out, box_growth[k, year], t0, width, box_growth_scale, sr, pan=box.pan, spread=0.15,
                   gain=0.25, per_col=1, root=root, steps=12, timbre=timbre, octave=12)

    # final change map: each box in turn, purple high, orange low, one shared scale
    box_purple = np.stack([_pool(b, 20) for b in g["box_purple"]])
    box_orange = np.stack([_pool(b, 20) for b in g["box_orange"]])
    change_scale = _scale(box_purple, box_orange)
    start = (nf.SCENES[3][0] + 18) / fps
    slot = (n / sr - start) / len(nf.BOXES)
    out = sections.new(start, n / sr)
    for k, box in enumerate(nf.BOXES):
        for layer, voice in ((box_purple[k], PURPLE), (box_orange[k], ORANGE)):
            _sweep(out, layer, start + k * slot, 0.9 * slot, change_scale, sr, pan=box.pan, spread=0.15,
                   gain=0.3, per_col=3, **voice)

    return sections.mix()
