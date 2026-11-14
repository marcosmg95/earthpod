"""SVS 5313 (Black Marble night lights) — the grid hums, the years tick, the regions sing.

The night-lights cousin of svs5196/co2_15 (breath + heartbeat + one instrument per region).

Background (has its own meaning, always there):
    hum     an electrical drone (G1 = 49 Hz, close to the 50 Hz mains of all four zoom regions):
            louder in the brighter years of each scene, brighter in tone while the lights grow, darker
            while they shrink; in the change maps, brighter the more of the picture is purple ("new lights")
    clock   one tick each time the year label changes (1 year = 1 beat; a lower "tock" for 2012)
Foreground: one instrument per region, entering when the movie shows it.
    Acts 1–2 (world map): three longitude bands of one copy of the map — Americas, Europe + Africa, Asia.
    Acts 3–4 (zoom boxes, from frame 668): Western Europe, Eastern Mediterranean, Ukraine, India.

Rules that keep the voices apart (as in co2_15):
    register follows latitude (north higher), pan follows longitude / box position (west left, east right),
    every voice uses the same D minor pentatonic, struck voices play two notes per year, sustained ones hold it.
Year scenes: each voice's note is its brightness that year, ranked against its other years (higher = brighter).
Change scenes: each region in turn plays a rising run (loudness = its purple "new lights") then a falling run
(loudness = its orange "lights out"); then all hold one note together: top of their range if purple wins,
bottom if orange wins.

Stem script: every layer has a live level slider (STEMS); everything else in PARAMS needs a re-render.
Iterate: uv run python -m jukebox.preview nightlights_grid --start 20 --end 32 --watch --set RUN_NOTES=3
"""
import numpy as np

from jukebox import instruments, mapping, nightlights_frames as nf, synth

TITLE = "Night lights: grid hum, year clock and regions"
DESCRIPTION = (
    "Background: a low electrical hum (louder in the brighter years of each scene, brighter in tone while the "
    "lights grow, darker while they shrink) and a soft clock tick each time the year label changes. "
    "Foreground: one instrument per region, entering when the movie shows it. On the world map: Americas "
    "marimba (left), Europe and Africa oboe (centre), Asia kalimba (right). With the zoom boxes: Western Europe "
    "vibraphone, Eastern Mediterranean harp, Ukraine flute, India cello, each panned to its box. Higher "
    "register = further north. In the year-by-year scenes each instrument's pitch is its region's brightness "
    "that year, ranked against its other years (higher note = brighter year). In the change maps each region "
    "in turn plays a rising run, as loud as its purple 'new lights', then a falling run, as loud as its "
    "orange 'lights out'; then all hold a final note, high where new lights win and low where lights went out. "
    "Data: brightness and colours measured from the NASA SVS 5313 movie (Black Marble night lights, "
    "2012–2023). These are picture indices, not calibrated radiance; map shading, labels and zooms affect them.")

# ---- mix (live sliders: no re-render) ----------------------------------------------------------------
HUM_GAIN = 0.10
CLOCK_GAIN = 0.20
AMERICAS_GAIN = 0.40        # marimba
EUROPE_AFRICA_GAIN = 0.30   # oboe
ASIA_GAIN = 0.40            # kalimba
WESTERN_EUROPE_GAIN = 0.35  # vibraphone
EAST_MED_GAIN = 0.40        # harp
UKRAINE_GAIN = 0.28         # flute
INDIA_GAIN = 0.30           # cello
OUTPUT_GAIN = 1.0

# ---- melody ------------------------------------------------------------------------------------------
STRUCK_SUBDIV = 2           # struck notes per year (2 = eighths of the year beat)
RANGE_SEMITONES = 12        # each voice spans this much above its lowest note
ACCENT = 0.70               # level of off-beat struck notes (1 = no accent)
PAN_WIDTH = 1.0             # 0 = all centred, 1 = the pans below
FADE_S = 1.0                # fade in / out of each group of voices
DUCK_DB = 3.0               # hum drops this much while instruments play
RUN_NOTES = 4               # notes per rising / falling run in the change scenes
CHORD_S = 1.8               # length of the final held note of each change scene
CHANGE_REST = 0.08          # run notes rest when their colour is below this share of the scene's loudest

# ---- hum (background) --------------------------------------------------------------------------------
HUM_HZ = 49.0               # G1: in the shared D minor pentatonic, close to 50 Hz mains
HUM_PARTIALS = 16
HUM_FLOOR = 0.35            # loudness of the dimmest year of a scene (brightest year = 1)
DARK_TILT, BRIGHT_TILT = 2.2, 0.9   # partial k has amplitude 1 / k**tilt (larger = darker)
SLOPE_SENS = 2.0            # how quickly the hum swings fully bright / dark with year-to-year change

# ---- clock (background) ------------------------------------------------------------------------------
TICK_MIDI, TOCK_MIDI = 86, 74       # D6 tick, D5 tock (first year of a scene)

STEMS = {"hum": "HUM_GAIN", "clock": "CLOCK_GAIN",
         "americas": "AMERICAS_GAIN", "europe_africa": "EUROPE_AFRICA_GAIN", "asia": "ASIA_GAIN",
         "western_europe": "WESTERN_EUROPE_GAIN", "east_med": "EAST_MED_GAIN",
         "ukraine": "UKRAINE_GAIN", "india": "INDIA_GAIN"}

PARAMS = {
    # levels (live)
    "HUM_GAIN": (0.0, 0.5), "CLOCK_GAIN": (0.0, 1.0),
    "AMERICAS_GAIN": (0.0, 1.0), "EUROPE_AFRICA_GAIN": (0.0, 1.0), "ASIA_GAIN": (0.0, 1.0),
    "WESTERN_EUROPE_GAIN": (0.0, 1.0), "EAST_MED_GAIN": (0.0, 1.0), "UKRAINE_GAIN": (0.0, 1.0),
    "INDIA_GAIN": (0.0, 1.0), "OUTPUT_GAIN": (0.0, 1.5),
    # melody
    "STRUCK_SUBDIV": (1, 4), "RANGE_SEMITONES": (5, 24), "ACCENT": (0.3, 1.0), "PAN_WIDTH": (0.0, 1.2),
    "FADE_S": (0.1, 4.0), "DUCK_DB": (0.0, 12.0), "RUN_NOTES": (2, 8), "CHORD_S": (0.5, 4.0),
    "CHANGE_REST": (0.0, 0.5),
    # hum
    "HUM_FLOOR": (0.0, 1.0), "SLOPE_SENS": (0.5, 8.0), "DARK_TILT": (1.0, 4.0), "BRIGHT_TILT": (0.3, 2.0),
}

# World-map bands: columns of nightlights_frames' world grid (64 columns, one copy of the map, west -> east;
# columns 22-24 are the dark Atlantic). Europe + Africa's lights sit further north (light-weighted row 4.1
# of 15, vs 5.2 for the other two), so it gets the highest register.
BANDS = {
    "americas":      dict(inst="marimba", low=62, pan=-0.70, cols=(0, 22)),    # D4
    "europe_africa": dict(inst="oboe",    low=67, pan=+0.00, cols=(22, 37)),   # G4
    "asia":          dict(inst="kalimba", low=57, pan=+0.70, cols=(37, 64)),   # A3
}
# Zoom boxes (nightlights_frames.BOXES, same order): lowest note by latitude, pan from the box on screen.
CITIES = {
    "western_europe": dict(box="weur", inst="vibraphone", low=69),  # A4 ~47N
    "east_med":       dict(box="emed", inst="harp",       low=62),  # D4 ~33N
    "ukraine":        dict(box="ukr",  inst="flute",      low=74),  # D5 ~49N
    "india":          dict(box="ind",  inst="cello",      low=50),  # D3 ~22N
}
BOX_PAN = {b.key: b.pan for b in nf.BOXES}
LABELS = {"americas": "Americas", "europe_africa": "Europe and Africa", "asia": "Asia",
          **{k: next(b.name for b in nf.BOXES if b.key == c["box"]) for k, c in CITIES.items()}}
SETTLE_FRAMES = 18          # a change map has faded in this many frames after its scene starts


def scene_start(key: str) -> int:
    return dict((k, f) for f, k, _ in nf.SCENES)[key]


def scene_end(key: str) -> int:
    keys = [k for _, k, _ in nf.SCENES]
    i = keys.index(key)
    return nf.SCENES[i + 1][0] if i + 1 < len(keys) else nf.FRAME_COUNT


def beat_s() -> float:
    """Nominal length of one year on screen (s): the clock's beat."""
    return float(np.median(np.diff(nf.YEAR_FRAMES["years"][1:]))) / nf.FPS


# ---- notes -------------------------------------------------------------------------------------------

Note = tuple[float, float, int, float]      # start s, length s, midi, velocity


def year_notes(values, scene: str, t_in: float, inst: str, notes: list[int]) -> list[Note]:
    """One pitch per year (its rank among the voice's years), from t_in to the end of the year scene."""
    struck = instruments.is_struck(inst)
    out: list[Note] = []
    for (a, b), v in zip(nf.year_windows(scene), instruments.ranks(values)):
        a, b = max(a / nf.FPS, t_in), b / nf.FPS
        if b - a < 0.05:
            continue
        v = float(v)
        midi = notes[int(round(v * (len(notes) - 1)))]
        if struck:   # STRUCK_SUBDIV notes per nominal year; longer years (the zoom-in) repeat the pattern
            slots = max(1, int(round((b - a) / (beat_s() / STRUCK_SUBDIV))))
            step = (b - a) / slots
            for k in range(slots):
                out.append((a + k * step, step, midi, (1.0 if k % STRUCK_SUBDIV == 0 else ACCENT) * (0.6 + 0.4 * v)))
        elif out and out[-1][2] == midi and abs(out[-1][0] + out[-1][1] - a) < 1e-6:
            s, d, m, vel = out[-1]                       # same pitch again: hold it (legato)
            out[-1] = (s, d + b - a, m, vel)
        else:
            out.append((a, b - a, midi, 0.8 + 0.2 * v))
    return out


def run_notes(purple: float, orange: float, loudest: float, t0: float, slot: float,
              notes: list[int]) -> list[Note]:
    """Rising run as loud as the purple share, then falling run as loud as the orange share, within `slot` s."""
    idx = np.round(np.linspace(0, len(notes) - 1, RUN_NOTES)).astype(int)
    step = min(slot / (2 * RUN_NOTES), beat_s())   # at most one note per year beat
    out: list[Note] = []
    for j, (amount, order) in enumerate(((purple, idx), (orange, idx[::-1]))):
        share = amount / loudest if loudest > 0 else 0.0
        if share < CHANGE_REST or share <= 0:
            continue
        vel = 0.35 + 0.65 * np.sqrt(share)
        for i, k in enumerate(order):
            out.append((t0 + (j * RUN_NOTES + i) * step, step, notes[k], float(vel)))
    return out


def change_notes(regions: dict[str, tuple[float, float]], scene: str, voices: dict[str, list[int]],
                 end: float) -> dict[str, list[Note]]:
    """Tour of the regions (west -> east), then all hold one note: top if purple wins, bottom if orange."""
    start = (scene_start(scene) + SETTLE_FRAMES) / nf.FPS
    chord_at = end - CHORD_S
    slot = (chord_at - start) / len(regions)
    loudest = max(max(p, o) for p, o in regions.values()) or 1.0
    widest = max(abs(p - o) for p, o in regions.values()) or 1.0
    out = {}
    for i, (name, (p, o)) in enumerate(regions.items()):
        notes = voices[name]
        out[name] = run_notes(p, o, loudest, start + i * slot, slot, notes)
        out[name].append((chord_at, CHORD_S, notes[-1] if p >= o else notes[0],
                          float(0.5 + 0.5 * np.sqrt(abs(p - o) / widest))))
    return out


def render_voice(inst: str, pan: float, notes: list[Note], env: np.ndarray, sr: int) -> np.ndarray:
    out = np.zeros((len(env), 2))
    pan = float(np.clip(pan * PAN_WIDTH, -1, 1))
    for t, dur, midi, vel in notes:
        synth.add_at(out, synth.pan_stereo(instruments.tone(inst, mapping.midi_to_hz(midi), dur, sr) * vel, pan),
                     t, sr)
    return synth.normalize(out * env[:, None])


# ---- hum and clock -----------------------------------------------------------------------------------

def hum_curves(table) -> tuple[np.ndarray, np.ndarray]:
    """Per frame: hum loudness (0..1) and brightness (0 = dark, 1 = bright), held over each year / change map."""
    level = np.ones(nf.FRAME_COUNT)
    bright = np.full(nf.FRAME_COUNT, 0.5)
    light = table.light.to_numpy(float)
    for scene in nf.YEAR_FRAMES:
        windows = nf.year_windows(scene)
        v = np.array([light[(a + b) // 2] for a, b in windows])   # mid-year frame: zooms have settled
        norm = (v - v.min()) / (np.ptp(v) or 1.0)
        diff = np.diff(v, prepend=v[0])
        slope = 0.5 + 0.5 * np.clip(SLOPE_SENS * diff / (np.abs(diff).max() or 1.0), -1, 1)
        for (a, b), lv, sl in zip(windows, norm, slope):
            level[a:b] = HUM_FLOOR + (1 - HUM_FLOOR) * lv
            bright[a:b] = sl
    for scene, frame in (("change", nf.CHANGE_FRAME), ("zoom_change", nf.ZOOM_CHANGE_FRAME)):
        p, o = table.purple.iloc[frame], table.orange.iloc[frame]
        a, b = scene_start(scene), scene_end(scene)
        level[a:b] = 1.0
        bright[a:b] = p / (p + o) if p + o > 0 else 0.5
    return level, bright


def hum_sound(level: np.ndarray, bright: np.ndarray, n: int, sr: int) -> np.ndarray:
    """The hum for given loudness (0..1) and brightness (0..1) curves (one value per sample), stereo."""
    t = np.arange(n) / sr
    tilt = DARK_TILT + (BRIGHT_TILT - DARK_TILT) * bright
    y = np.zeros(n)
    power = np.zeros(n)
    for k in range(1, HUM_PARTIALS + 1):
        a = np.exp(-tilt * np.log(k))
        y += a * np.sin(2 * np.pi * k * HUM_HZ * t + 0.7 * k)
        power += a * a
    y *= level / np.sqrt(power)               # same loudness whatever the brightness
    y *= 1 + 0.06 * np.sin(2 * np.pi * 0.7 * t)
    return synth.normalize(synth.pan_stereo(y, 0.0))


def tick(midi: int, level: float, sr: int) -> np.ndarray:
    n = int(0.09 * sr)
    t = np.arange(n) / sr
    body = np.sin(2 * np.pi * mapping.midi_to_hz(midi) * t) * np.exp(-55 * t)
    click = synth.band_noise(n, 2500, 7000, sr, seed=131) * np.exp(-140 * t)
    return (body + 0.4 * click) * np.minimum(1.0, t / 0.001) * level


def render_clock(n: int, sr: int) -> np.ndarray:
    out = np.zeros((n, 2))
    for frames in nf.YEAR_FRAMES.values():
        for i, frame in enumerate(frames):
            y = tick(TOCK_MIDI, 1.0, sr) if i == 0 else tick(TICK_MIDI, 0.6, sr)
            synth.add_at(out, synth.pan_stereo(y, 0.0), frame / nf.FPS, sr)
    return synth.normalize(out)


# ---- render ------------------------------------------------------------------------------------------

def render(ctx):
    f, g = ctx.nightlights_features(), ctx.nightlights_grids()
    n, sr = ctx.n_samples, ctx.sr
    end = n / sr
    bands_out = scene_start("zoom_years") / nf.FPS + FADE_S     # final chord rings into the zoom-in
    cities_in = nf.BOXES_IN[0] / nf.FPS
    env_bands = instruments.window(n, sr, -FADE_S, bands_out, FADE_S)
    env_cities = instruments.window(n, sr, cities_in, end + FADE_S, FADE_S)

    stems = {}
    # world bands: yearly brightness, then the world change map
    band_scale = {k: instruments.scale_notes(b["low"], RANGE_SEMITONES) for k, b in BANDS.items()}
    band_change = {k: (float(g["world_purple"][:, slice(*b["cols"])].sum()),
                       float(g["world_orange"][:, slice(*b["cols"])].sum())) for k, b in BANDS.items()}
    tour = change_notes(band_change, "change", band_scale, scene_end("change") / nf.FPS)
    for k, b in BANDS.items():
        yearly = g["world_light"][:, :, slice(*b["cols"])].sum(axis=(1, 2))
        notes = year_notes(yearly, "years", 0.0, b["inst"], band_scale[k]) + tour[k]
        stems[k] = render_voice(b["inst"], b["pan"], notes, env_bands, sr)

    # zoom boxes: yearly brightness from the moment they appear, then the zoomed change map
    keys = [b.key for b in nf.BOXES]
    city_scale = {k: instruments.scale_notes(c["low"], RANGE_SEMITONES) for k, c in CITIES.items()}
    city_change = {k: (float(g["box_purple"][keys.index(c["box"])].sum()),
                       float(g["box_orange"][keys.index(c["box"])].sum())) for k, c in CITIES.items()}
    tour = change_notes(city_change, "zoom_change", city_scale, end - 0.3)
    for k, c in CITIES.items():
        yearly = g["box_light"][keys.index(c["box"])].sum(axis=(1, 2))
        notes = year_notes(yearly, "zoom_years", cities_in, c["inst"], city_scale[k]) + tour[k]
        stems[k] = render_voice(c["inst"], BOX_PAN[c["box"]], notes, env_cities, sr)

    level, bright = hum_curves(f.table)
    duck = 10 ** (-DUCK_DB * np.maximum(env_bands, env_cities) / 20)
    hum = hum_sound(nf.frame_envelope(level, n, sr), nf.frame_envelope(bright, n, sr), n, sr)
    return {"hum": hum * duck[:, None], "clock": render_clock(n, sr), **stems}


# ---- sound legend: one short clip per layer, for learning the sounds before the movie ----------------

def samples(sr: int = synth.SR) -> dict[str, tuple[str, np.ndarray]]:
    """name -> (spoken explanation, short stereo clip). Same sound models and pans as render()."""
    out = {}
    n = int(6.0 * sr)
    t = np.arange(n) / sr
    out["hum"] = ("Hum: the electrical grid. Louder in brighter years, brighter in tone while the lights grow, "
                  "darker as they shrink.",
                  hum_sound(HUM_FLOOR + (1 - HUM_FLOOR) * np.sin(np.pi * t / t[-1]),
                            (t < t[-1] / 2).astype(float), n, sr))
    beat = beat_s()
    clip = np.zeros((int(7 * beat * sr), 2))
    for i in range(6):
        y = tick(TOCK_MIDI, 1.0, sr) if i == 0 else tick(TICK_MIDI, 0.6, sr)
        synth.add_at(clip, synth.pan_stereo(y, 0.0), i * beat, sr)
    out["clock"] = ("Clock: one tick per year on screen. The lower tock is 2012, the first year.",
                    synth.normalize(clip))
    voices = {**{k: (b["inst"], b["low"], b["pan"]) for k, b in BANDS.items()},
              **{k: (c["inst"], c["low"], BOX_PAN[c["box"]]) for k, c in CITIES.items()}}
    for name, (inst, low, pan) in voices.items():
        scale = instruments.scale_notes(low, RANGE_SEMITONES)
        step = 0.4 if instruments.is_struck(inst) else 0.7
        clip = np.zeros((int((len(scale) * step + 2.0) * sr), 2))
        pan = float(np.clip(pan * PAN_WIDTH, -1, 1))
        for i, midi in enumerate(scale):
            y = instruments.tone(inst, mapping.midi_to_hz(midi), step, sr) * (0.6 + 0.4 * i / (len(scale) - 1))
            synth.add_at(clip, synth.pan_stereo(y, pan), i * step, sr)
        label = LABELS[name]
        side = "on the left" if pan < -0.2 else "on the right" if pan > 0.2 else "in the centre"
        out[name] = (f"{label}: {inst}, heard {side}. Low notes mean a dimmer year, high notes a brighter one.",
                     synth.normalize(clip))
    return out
