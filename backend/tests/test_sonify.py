import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from jukebox import frames, instruments, mapping, nightlights_frames, sonify, svs, synth


class TestTimeline(unittest.TestCase):
    def test_spans_merge_runs(self):
        tl = sonify.Timeline(["1990", "1990", "1990", "1991", "1991.0", "x"], fps=3)
        self.assertEqual(tl.duration, 2.0)
        self.assertEqual(tl.spans(), [("1990", 0.0, 1.0), ("1991", 1.0, 1 + 1 / 3),
                                      ("1991.0", 1 + 1 / 3, 5 / 3), ("x", 5 / 3, 2.0)])
        self.assertEqual(sonify.label_year("1991.0"), 1991)
        self.assertIsNone(sonify.label_year("x"))

    def test_linear(self):
        tl = sonify.Timeline.linear(2000, 2003, duration_s=4, fps=2)
        self.assertEqual(len(tl.labels), 8)
        self.assertEqual([s[0] for s in tl.spans()], ["2000", "2001", "2002", "2003"])


class TestSvsTimeline(unittest.TestCase):
    def test_fps_and_dirs(self):
        data = {"media_groups": [{"title": "", "items": [
            {"instance": {"url": "http://svs.gsfc.nasa.gov/vis/a000000/a005400/a005450/m.mp4",
                          "filename": "m.mp4", "media_type": "Movie"}},
            {"instance": {"url": "http://svs.gsfc.nasa.gov/vis/a000000/a005400/a005450/frames/3840x2160_16x9_30p/",
                          "filename": "3840x2160_16x9_30p", "media_type": "Frames"}},
        ]}]}
        self.assertEqual(svs.fps_from_frames(svs.media_items(data)), 30.0)
        self.assertEqual(svs.vis_dirs(data), ["https://svs.gsfc.nasa.gov/vis/a000000/a005400/a005450/"])


class TestContext(unittest.TestCase):
    def setUp(self):
        self.ctx = sonify.SonifyContext(1, sonify.Timeline(["2000"] * 2 + ["2001"] * 2 + ["2002"] * 2, fps=2))

    def test_notes_follow_timeline(self):
        series = pd.Series({2000: 0.0, 2002: 0.3})          # 2001 missing -> no note
        notes = self.ctx.notes_from_series(series, mapping.DEFAULT_VOICES[0])
        self.assertEqual([(n.year, n.start, n.dur) for n in notes], [(2000, 0.0, 1.0), (2002, 2.0, 1.0)])
        self.assertEqual(notes[1].midi, mapping.value_to_midi(0.3, 0.1, mapping.TONIC_MIDI))

    def test_run_pads_to_duration_and_wav(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "short.py"
            p.write_text("import numpy as np\ndef render(ctx):\n    return np.ones(100) * 2\n")
            self.assertEqual(list(sonify.discover(d)), ["short"])
            y = sonify.run(p, self.ctx)
        self.assertEqual(y.shape, (self.ctx.n_samples, 2))
        self.assertEqual(y.max(), 1.0)                       # clipped
        self.assertEqual(y[-1].tolist(), [0.0, 0.0])         # padded
        wav = synth.wav_bytes(y, self.ctx.sr)
        self.assertEqual(wav[:4], b"RIFF")

    def test_discover_sorts_numbers_naturally(self):
        names = ["co2_10_beat", "co2_2_beat", "co2_1_beat", "co2_13_beat",
                 "co2_2_take10", "co2_2_take2", "gistemp_lead", "_hidden"]
        with tempfile.TemporaryDirectory() as d:
            for name in names:
                (Path(d) / f"{name}.py").touch()
            self.assertEqual(list(sonify.discover(d)), [
                "co2_1_beat", "co2_2_beat", "co2_2_take2", "co2_2_take10",
                "co2_10_beat", "co2_13_beat", "gistemp_lead",
            ])

    def test_discover_for_page(self):
        with tempfile.TemporaryDirectory() as d:
            for rel in ["generic.py", "svs5196/co2_a.py", "svs5313/night_a.py"]:
                (Path(d) / rel).parent.mkdir(exist_ok=True)
                (Path(d) / rel).touch()
            self.assertEqual(list(sonify.discover_for(d, 5196)), ["generic", "co2_a"])
            self.assertEqual(list(sonify.discover_for(d, 5313)), ["generic", "night_a"])
            self.assertEqual(list(sonify.discover_for(d, 9999)), ["generic"])
            self.assertEqual(sonify.folder_for(d, 5196), Path(d) / "svs5196")

    def test_real_folders_match_their_page(self):
        root = Path(__file__).resolve().parents[1] / "sonifications"
        for sub in root.glob("svs*"):
            for name, path in sonify.discover(sub).items():
                with self.subTest(name):
                    self.assertIn(f"SVS {sub.name[3:]}", sonify.load(path).DESCRIPTION + (sonify.load(path).__doc__ or ""))

    def test_demo_script(self):
        ctx = sonify.SonifyContext(5450, sonify.Timeline.linear(1880, 1889, 2, 30))
        y = sonify.run(Path(__file__).resolve().parents[1] / "sonifications" / "svs5450" / "gistemp_lead.py", ctx)
        self.assertEqual(y.shape, (ctx.n_samples, 2))
        self.assertGreater(abs(y).max(), 0.1)


class TestNightLights(unittest.TestCase):
    SCRIPT = Path(__file__).resolve().parents[1] / "sonifications" / "svs5313" / "nightlights_nervous_system.py"

    def test_measure_masks_legend_and_tracks_position(self):
        image = np.zeros((270, 960, 3), dtype=np.uint8)
        image[120:180, 420:550] = 255
        m = nightlights_frames.measure(image)
        self.assertEqual((m["light"], m["x"]), (0.0, 0.5))
        self.assertEqual(list(m), nightlights_frames.COLUMNS)
        image[30:50, 20:40] = 255
        m = nightlights_frames.measure(image)
        self.assertGreater(m["light"], 0)
        self.assertLess(m["x"], 0.2)

    @staticmethod
    def _paint(hue, sat, rect=(0.1, 0.1, 0.2, 0.2)):
        import cv2
        hsv = np.zeros((270, 960, 3), dtype=np.uint8)
        x0, y0, x1, y1 = rect
        hsv[int(270 * y0):int(270 * y1), int(960 * x0):int(960 * x1)] = (hue, sat, 230)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    def test_change_colours_are_told_apart_from_gold_year_lights(self):
        gold = nightlights_frames.measure(self._paint(24, 80))      # year-map lights
        purple = nightlights_frames.measure(self._paint(135, 110))  # legend "new lights"
        orange = nightlights_frames.measure(self._paint(13, 140))   # legend "lights out"
        self.assertGreater(gold["light"], 0)
        self.assertEqual((gold["purple"], gold["orange"]), (0.0, 0.0))
        self.assertGreater(purple["purple"], 0)
        self.assertEqual(purple["orange"], 0.0)
        self.assertGreater(orange["orange"], 0)
        self.assertEqual(orange["purple"], 0.0)

    def test_box_features_only_see_their_box(self):
        india = next(b for b in nightlights_frames.BOXES if b.key == "ind")
        m = nightlights_frames.measure(self._paint(135, 110, india.rect))
        self.assertGreater(m["ind_purple"], 0)
        self.assertEqual(m["weur_purple"] + m["emed_purple"] + m["ukr_purple"], 0.0)
        self.assertGreater(india.pan, 0.5)
        self.assertLess(nightlights_frames.BOXES[0].pan, -0.5)

    def test_scene_labels_and_sections(self):
        labels = nightlights_frames.labels()
        self.assertEqual(len(labels), nightlights_frames.FRAME_COUNT)
        self.assertEqual(labels[0], "2012 · global map")
        self.assertEqual(labels[14], "2012 · global map")
        self.assertEqual(labels[15], "2013 · global map")
        self.assertEqual(labels[193], "2023 · global map")
        self.assertEqual(labels[400], "Change 2012–2023 · global change map")
        self.assertEqual(labels[700], "2012 · regional zooms")
        self.assertEqual(labels[1008], "2023 · regional zooms")
        self.assertEqual(labels[1299], "Change 2012–2023 · regional zooms")
        starts = [frame for _, frame in nightlights_frames.SECTIONS]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(len(nightlights_frames.year_change_frames()), 22)

    def test_committed_features_match_the_scenes(self):
        f = nightlights_frames.load(5313, nightlights_frames.MOVIE)
        scene = nightlights_frames.scene_of(f.table.frame)
        colour = f.table.purple + f.table.orange
        change = colour[scene == "change"].mean()
        self.assertGreater(change, 0.0)
        self.assertLess(colour[scene == "years"].max(), 0.02 * change)  # gold year lights: compression noise only
        boxes = f.table[[f"{b.key}_light" for b in nightlights_frames.BOXES]].sum(axis=1)
        self.assertGreater(boxes[700], 5 * boxes[600])               # boxes fade in at frames 668-690

    def test_feature_timing(self):
        f = nightlights_frames.NightLightsFeatures(pd.DataFrame({"light": [0.0, 1.0, 0.0]}))
        samples = f.resampled("light", 12, 120)
        self.assertEqual(samples[4], 1.0)
        self.assertEqual(samples[8], 0.0)

    def test_movie_and_timeline_validation(self):
        movie = nightlights_frames.MOVIE
        self.assertIsNone(nightlights_frames.load(5196, movie))
        self.assertIsNone(nightlights_frames.load(5313, "other.mp4"))
        ctx = sonify.SonifyContext(5313, sonify.Timeline(["frame"] * 1300, 29), movie=movie)
        with self.assertRaises(ValueError):
            ctx.nightlights_features()
        ctx.timeline = sonify.Timeline(["frame"] * 1299, 30)
        with self.assertRaises(ValueError):
            ctx.nightlights_features()

    def test_real_movie_renders_and_silence_stays_silent(self):
        f = nightlights_frames.load(5313, nightlights_frames.MOVIE)
        self.assertIsNotNone(f)
        ctx = sonify.SonifyContext(5313, sonify.Timeline(["frame"] * len(f.table), 30),
                                   movie=nightlights_frames.MOVIE, sr=8000)
        audio = sonify.run(self.SCRIPT, ctx)
        self.assertEqual(audio.shape, (ctx.n_samples, 2))
        self.assertGreater(np.max(np.abs(audio)), 0.1)
        self.assertTrue(np.isfinite(audio).all())
        f.table["light"] = 0.0
        with patch.object(ctx, "nightlights_features", return_value=f):
            self.assertFalse(np.any(sonify.run(self.SCRIPT, ctx)))

    def test_pan_follows_screen_position(self):
        mod = sonify.load(self.SCRIPT)
        ctx = sonify.SonifyContext(5313, sonify.Timeline(["frame"] * 60, 30), sr=8000)
        f = nightlights_frames.NightLightsFeatures(pd.DataFrame({
            "light": np.ones(60), "x": np.full(60, 0.1),
        }))
        with patch.object(ctx, "nightlights_features", return_value=f):
            left = mod.render(ctx)
            f.table["x"] = 0.9
            right = mod.render(ctx)
        self.assertGreater(np.linalg.norm(left[:, 0]), np.linalg.norm(left[:, 1]))
        self.assertGreater(np.linalg.norm(right[:, 1]), np.linalg.norm(right[:, 0]))

    def test_murmur_follows_light_over_time(self):
        mod = sonify.load(self.SCRIPT)
        ctx = sonify.SonifyContext(5313, sonify.Timeline(["frame"] * 60, 30), sr=8000)
        f = nightlights_frames.NightLightsFeatures(pd.DataFrame({
            "light": np.r_[np.zeros(30), np.ones(30)], "x": np.full(60, 0.5),
        }))
        with patch.object(ctx, "nightlights_features", return_value=f):
            audio = mod.render(ctx)
        self.assertFalse(np.any(audio[:ctx.sr // 2]))
        self.assertGreater(np.max(np.abs(audio[ctx.sr:])), 0.1)


class TestNightLightsThreeActs(unittest.TestCase):
    SCRIPT = Path(__file__).resolve().parents[1] / "sonifications" / "svs5313" / "nightlights_three_acts.py"
    SR = 8000

    def _ctx(self):
        return sonify.SonifyContext(5313, sonify.Timeline(nightlights_frames.labels(), 30),
                                    movie=nightlights_frames.MOVIE, sr=self.SR)

    @staticmethod
    def _dark():
        nb, ny = len(nightlights_frames.BOXES), len(nightlights_frames.YEAR_FRAMES["years"])
        w, b = nightlights_frames.WORLD_GRID, nightlights_frames.BOX_GRID
        return {"world_light": np.zeros((ny, *w)), "world_purple": np.zeros(w), "world_orange": np.zeros(w),
                "box_light": np.zeros((nb, ny, *b)), "box_purple": np.zeros((nb, *b)), "box_orange": np.zeros((nb, *b))}

    def _render(self, grids):
        ctx = self._ctx()
        with patch.object(ctx, "nightlights_grids", return_value=grids):
            return sonify.run(self.SCRIPT, ctx)

    def _span(self, audio, f0, f1):
        return audio[int(f0 / 30 * self.SR):int(f1 / 30 * self.SR)]

    def _centroid(self, audio, f0, f1):
        mono = self._span(audio, f0, f1).sum(axis=1)
        spec = np.abs(np.fft.rfft(mono))
        return (np.fft.rfftfreq(len(mono), 1 / self.SR) * spec).sum() / spec.sum()

    def test_real_movie_renders_every_section(self):
        ctx = self._ctx()
        audio = sonify.run(self.SCRIPT, ctx)
        self.assertEqual(audio.shape, (ctx.n_samples, 2))
        self.assertTrue(np.isfinite(audio).all())
        for f0, f1 in [(15, 270), (310, 420), (420, 530), (535, 630), (690, 830), (830, 1100), (1130, 1290)]:
            self.assertGreater(np.max(np.abs(self._span(audio, f0, f1))), 0.05)

    def test_dark_grids_are_silent(self):
        self.assertFalse(np.any(self._render(self._dark())))

    def test_purple_sounds_higher_than_orange(self):
        g = self._dark()
        g["world_purple"][7, 20:40] = 1.0
        high = self._centroid(self._render(g), 305, 630)
        g["world_purple"][:], g["world_orange"][7, 20:40] = 0.0, 1.0
        self.assertGreater(high, 2 * self._centroid(self._render(g), 305, 630))

    def test_north_is_higher_and_west_is_left(self):
        def lit(row, col):
            g = self._dark()
            g["world_light"][:, row, col] = 1.0
            return self._render(g)
        north, south = lit(0, 10), lit(14, 10)
        self.assertGreater(self._centroid(north, 15, 270), 1.5 * self._centroid(south, 15, 270))
        west, east = self._span(lit(7, 2), 15, 270), self._span(lit(7, 60), 15, 270)
        self.assertGreater(np.linalg.norm(west[:, 0]), 2 * np.linalg.norm(west[:, 1]))
        self.assertGreater(np.linalg.norm(east[:, 1]), 2 * np.linalg.norm(east[:, 0]))

    def test_box_voice_sits_at_its_box(self):
        def box_audio(key):
            g = self._dark()
            g["box_light"][[b.key for b in nightlights_frames.BOXES].index(key)] = 1.0
            return self._span(self._render(g), 830, 1100)
        left, right = box_audio("weur"), box_audio("ind")
        self.assertGreater(np.linalg.norm(left[:, 0]), 2 * np.linalg.norm(left[:, 1]))
        self.assertGreater(np.linalg.norm(right[:, 1]), 2 * np.linalg.norm(right[:, 0]))

    def test_grids_need_the_measured_movie(self):
        self.assertIsNone(nightlights_frames.load_grids(5196, nightlights_frames.MOVIE))
        with self.assertRaises(LookupError):
            sonify.SonifyContext(5313, sonify.Timeline(["x"] * 3, 30), movie="other.mp4").nightlights_grids()

    def test_real_grids_show_the_lights_growing(self):
        g = nightlights_frames.load_grids(5313, nightlights_frames.MOVIE)
        self.assertGreater(g["world_light"][-1].sum(), 1.2 * g["world_light"][0].sum())
        ind = [b.key for b in nightlights_frames.BOXES].index("ind")
        self.assertGreater(g["box_light"][ind, -1].sum(), 1.5 * g["box_light"][ind, 0].sum())


class TestNightLightsGridAndRegions(unittest.TestCase):
    SCRIPT = Path(__file__).resolve().parents[1] / "sonifications" / "svs5313" / "nightlights_grid_and_regions.py"
    SR = 8000

    @classmethod
    def setUpClass(cls):
        cls.mod = sonify.load(cls.SCRIPT)
        cls.ctx = sonify.SonifyContext(5313, sonify.Timeline(nightlights_frames.labels(), 30),
                                       movie=nightlights_frames.MOVIE, sr=cls.SR)
        cls.stems = sonify.render_stems(cls.SCRIPT, cls.ctx)

    def _rms(self, stem, t0, t1):
        a = self.stems.audio[stem][int(t0 * self.SR):int(t1 * self.SR)]
        return float(np.sqrt((a ** 2).mean()))

    def test_every_stem_plays_and_mixes_live(self):
        self.assertEqual(set(self.stems.audio), set(self.mod.STEMS))
        for name, audio in self.stems.audio.items():
            with self.subTest(name):
                self.assertEqual(audio.shape, (self.ctx.n_samples, 2))
                self.assertTrue(np.isfinite(audio).all())
                self.assertGreater(np.abs(audio).max(), 0.05)
        self.assertLessEqual(np.abs(self.stems.mix()).max(), 1.0)

    def test_bands_hand_over_to_the_zoom_boxes(self):
        for band in self.mod.BANDS:
            self.assertGreater(self._rms(band, 0.5, 9.5), 0.003)
            self.assertEqual(self._rms(band, 25, 43), 0.0)
        for city in self.mod.CITIES:
            self.assertEqual(self._rms(city, 0, 21), 0.0)
            self.assertGreater(self._rms(city, 28, 36), 0.003)

    def test_box_voices_sit_at_their_boxes(self):
        west, east = self.stems.audio["western_europe"], self.stems.audio["india"]
        self.assertGreater(np.linalg.norm(west[:, 0]), 2 * np.linalg.norm(west[:, 1]))
        self.assertGreater(np.linalg.norm(east[:, 1]), 2 * np.linalg.norm(east[:, 0]))

    def test_final_note_is_high_for_new_lights_and_low_for_lights_out(self):
        scale = {"a": [60, 62, 65], "b": [60, 62, 65]}
        notes = self.mod.change_notes({"a": (3.0, 1.0), "b": (1.0, 3.0)}, "zoom_change", scale, 43.0)
        self.assertEqual(notes["a"][-1][2], 65)
        self.assertEqual(notes["b"][-1][2], 60)
        up = [n[2] for n in notes["a"][:self.mod.RUN_NOTES]]
        self.assertEqual(up, sorted(up))

    def test_ukraine_dims_in_2022(self):
        g = self.ctx.nightlights_grids()
        k = [b.key for b in nightlights_frames.BOXES].index("ukr")
        c = self.mod.CITIES["ukraine"]
        scale = instruments.scale_notes(c["low"], self.mod.RANGE_SEMITONES)
        notes = self.mod.year_notes(g["box_light"][k].sum(axis=(1, 2)), "zoom_years",
                                    nightlights_frames.BOXES_IN[0] / 30, c["inst"], scale)
        def pitch(year):   # the note sounding in the middle of that year on screen
            a, b = nightlights_frames.year_windows("zoom_years")[year - nightlights_frames.FIRST_YEAR]
            t = (a + b) / 2 / 30
            return next(m for start, dur, m, _ in notes if start <= t < start + dur)
        self.assertLess(pitch(2022), pitch(2021))

    def test_legend_has_a_clip_per_stem(self):
        self.assertEqual(set(self.mod.samples(self.SR)), set(self.mod.STEMS))


class TestInstruments(unittest.TestCase):
    def test_ranks(self):
        np.testing.assert_allclose(instruments.ranks([5.0, 1.0, 3.0]), [1.0, 0.0, 0.5])
        np.testing.assert_allclose(instruments.ranks([2.0, 2.0]), [0.5, 0.5])

    def test_scale_notes_stay_in_d_minor_pentatonic(self):
        for m in instruments.scale_notes(57, 12):
            self.assertIn((m - mapping.TONIC_MIDI) % 12, mapping.SCALE)


class TestSynthTimbres(unittest.TestCase):
    def test_every_timbre_is_pitched(self):
        for timbre in ("pluck", "string", "soft", "bell"):
            y = synth.tone(440.0, 0.5, timbre, 8000)
            spec = np.abs(np.fft.rfft(y[200:2200]))
            peak_hz = np.fft.rfftfreq(2000, 1 / 8000)[spec.argmax()]
            self.assertAlmostEqual(peak_hz, 440.0, delta=250, msg=timbre)
            self.assertLess(abs(y.mean()), 0.05 * np.abs(y).max(), msg=f"{timbre} has a DC offset")


class TestStems(unittest.TestCase):
    """Stem scripts: render() returns named layers, STEMS names the constant that sets each level."""
    SCRIPT = """\
import numpy as np
A_GAIN = 0.5
B_GAIN = 0.25
OUTPUT_GAIN = 0.8
PITCH = 2
STEMS = {'a': 'A_GAIN', 'b': 'B_GAIN'}
PARAMS = {'A_GAIN': (0, 1), 'B_GAIN': (0, 1), 'OUTPUT_GAIN': (0, 1), 'PITCH': (1, 4)}
def render(ctx):
    t = np.arange(ctx.n_samples) / ctx.sr
    return {'a': np.sin(2 * np.pi * 100 * PITCH * t) * 0.5, 'b': np.column_stack([t * 0, t * 0 + 0.4])}
"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "stems.py"
        self.path.write_text(self.SCRIPT)
        self.ctx = sonify.SonifyContext(1, sonify.Timeline(["2000"] * 10, fps=10), sr=8000)

    def tearDown(self):
        self.tmp.cleanup()

    def test_mix_matches_run_and_levels_need_no_render(self):
        stems = sonify.render_stems(self.path, self.ctx)
        self.assertEqual(list(stems.audio), ["a", "b"])
        self.assertEqual(stems.params, {"a": "A_GAIN", "b": "B_GAIN"})
        self.assertEqual((stems.gains, stems.output, stems.normalize), ({"a": 0.5, "b": 0.25}, 0.8, True))
        np.testing.assert_allclose(sonify.run(self.path, self.ctx), stems.mix())
        self.assertAlmostEqual(np.abs(stems.mix()).max(), 0.8 * 10 ** (-6 / 20), places=6)
        # a level override changes only the mix: same as re-mixing the stems already rendered
        self.ctx.params = {"B_GAIN": 0.0}
        np.testing.assert_allclose(sonify.run(self.path, self.ctx), stems.mix({"b": 0.0}))
        self.assertEqual(sonify.mix_params(sonify.load(self.path)), {"A_GAIN", "B_GAIN", "OUTPUT_GAIN"})

    def test_plain_script_is_one_stem_played_as_is(self):
        self.path.write_text("import numpy as np\ndef render(ctx):\n    return np.full(ctx.n_samples, 0.3)\n")
        stems = sonify.render_stems(self.path, self.ctx)
        self.assertEqual((list(stems.audio), stems.params, stems.normalize), (["mix"], {}, False))
        self.assertAlmostEqual(stems.mix().max(), 0.3)
        self.assertEqual(sonify.mix_params(sonify.load(self.path)), set())

    def test_stems_must_match_render(self):
        self.path.write_text(self.SCRIPT.replace("STEMS = {'a'", "STEMS = {'c': 'A_GAIN', 'a'"))
        with self.assertRaises(ValueError):
            sonify.render_stems(self.path, self.ctx)


class TestLivePlayer(unittest.TestCase):
    @staticmethod
    def _module():
        import importlib.util
        import sys
        path = Path(__file__).resolve().parents[1] / "apps" / "live_player.py"
        spec = importlib.util.spec_from_file_location("live_player", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["live_player"] = mod          # declare_component looks its caller up in sys.modules
        spec.loader.exec_module(mod)
        return mod

    def test_download_is_the_mix_with_current_levels(self):
        lp = self._module()
        sr = 8000
        t = np.arange(sr) / sr
        stems = sonify.Stems({"a": np.column_stack([np.sin(2 * np.pi * 220 * t)] * 2) * 0.5,
                              "b": np.column_stack([np.sin(2 * np.pi * 330 * t)] * 2) * 0.5},
                             {"a": 1.0, "b": 1.0}, {"a": "A", "b": "B"}, 0.9, True)
        wavs = lp.stem_wavs(stems, sr)
        got = lp.wav_to_array(lp.mix_wav(wavs, {"a": 0.2, "b": 1.0}, 0.5, True, sr))
        want = sonify.Stems({k: lp.wav_to_array(w) for k, w in wavs.items()}, {"a": 0.2, "b": 1.0}, {}, 0.5,
                            True).mix()
        np.testing.assert_allclose(got, want, atol=2 / 32767)
        self.assertEqual(lp.mix_wav({"mix": wavs["a"]}, {}, 1.0, False, sr), wavs["a"])

    def test_mix_spec_lists_level_sliders(self):
        lp = self._module()
        stems = sonify.Stems({}, {"a": 0.5}, {"a": "A_GAIN"}, 0.8, True)
        specs = {"A_GAIN": sonify.Param("A_GAIN", 0.5, 0.0, 1.0), "OUTPUT_GAIN": sonify.Param("OUTPUT_GAIN", 0.8, 0.0, 1.0)}
        spec = lp.mix_spec(stems, specs, {"A_GAIN": 0.1})
        self.assertEqual(spec["stems"], [{"stem": "a", "param": "A_GAIN", "value": 0.1, "lo": 0.0, "hi": 1.0}])
        self.assertEqual(spec["output"]["value"], 0.8)


class TestSyncPlayer(unittest.TestCase):
    @staticmethod
    def _module():
        import importlib.util
        path = Path(__file__).resolve().parents[1] / "apps" / "sync_player.py"
        spec = importlib.util.spec_from_file_location("sync_player", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_chapters_are_embedded_safely(self):
        html = self._module().player_html("https://x/movie.mp4", b"RIFF", [("2012", 0.0, 1.0)], 1.0, 300,
                                          chapters=[("1 · Years", 0.0), ("</script>", 9.6333)])
        self.assertIn('const chapters = [["1 \\u00b7 Years", 0.0], ["\\u003c/script>", 9.6333]];', html)
        self.assertNotIn("__CHAPTERS__", html)
        self.assertEqual(html.count("</script>"), 1)

    def test_no_chapters_hides_the_nav(self):
        html = self._module().player_html("https://x/movie.mp4", b"RIFF", [], 1.0, 300)
        self.assertIn("const chapters = [];", html)


class TestCo2Scripts(unittest.TestCase):
    """SVS 5196 scripts run on the committed frame features (data/derived/svs5196_*)."""
    MOVIE = "dyamondPointCloud_12-1-2023b_dyamond_co2_anim_globe_orbit_1080p30_h265.mp4"
    FOLDER = Path(__file__).resolve().parents[1] / "sonifications" / "svs5196"

    def test_movie_tags(self):
        self.assertEqual(frames.movie_tag(self.MOVIE), "orbit")
        self.assertEqual(frames.movie_tag("x_dyamond_co2_anim_globe_zoom_2160p30.mp4"), "zoom")
        self.assertEqual(frames.movie_tag("x_dyamond_co2_anim_globe_zoomwest_3x3hyperwall_1080p30_2.mp4"), "zoomwest")
        self.assertIsNone(frames.movie_tag("x_dyamond_co2_anim_globe_zoom_5x3_1080p30.mp4"))
        self.assertIsNone(frames.load(5450, self.MOVIE))

    def test_orbit_features(self):
        f = frames.load(5196, self.MOVIE)
        self.assertEqual(f.profiles.shape, (len(f.table), frames.PROFILE_COLS))
        self.assertEqual(f.table.label.iloc[0], "14 Jan 2020 22:00")      # 1 frame = 1 model hour
        self.assertEqual(f.table.label.iloc[1174], "03 Mar 2020 20:00")   # as printed on that frame
        self.assertTrue(f.dated)
        self.assertFalse(frames.load(5196, "x_globe_tilt_1080p30.mp4").dated)

    def test_scripts_render(self):
        f = frames.load(5196, self.MOVIE)
        ctx = sonify.SonifyContext(5196, sonify.Timeline(f.table.label.tolist(), 30.0), movie=self.MOVIE)
        scripts = sonify.discover(self.FOLDER)
        self.assertEqual(len(scripts), 15)
        for name, path in scripts.items():
            with self.subTest(name):
                mod = sonify.load(path)
                self.assertIn("SVS 5196", mod.DESCRIPTION)             # names its data source
                y = sonify.run(path, ctx)
                self.assertEqual(y.shape, (ctx.n_samples, 2))
                self.assertGreater(abs(y).max(), 0.1)
                self.assertLess((abs(y) >= 1).mean(), 0.001)           # not clipping

    def test_currents_position_spread_and_silence(self):
        mod = sonify.load(self.FOLDER / "co2_8_currents.py")
        table = pd.DataFrame({
            "plume": [1.0] * 8 + [0.0] * 4,
            "x": [0.25] * 4 + [0.75] * 4 + [0.5] * 4,
            "y": [0.75] * 4 + [0.25] * 4 + [0.5] * 4,
        })
        profiles = np.zeros((12, 5))
        profiles[:4, 1] = 1
        profiles[4:8, [0, 4]] = 1
        f = frames.FrameFeatures("orbit", table, profiles)
        ctx = sonify.SonifyContext(5196, sonify.Timeline(["frame"] * 12, 30), sr=8000)
        notes = mod.notes_for(f, ctx.frame_times, ctx.timeline.fps)
        self.assertEqual(len(notes), 4)  # narrow tone, then a wide chord, then silence
        self.assertEqual(notes[0].pan, -0.5)
        self.assertTrue(all(n.pan == 0.5 for n in notes[1:]))
        self.assertGreater(notes[2].midi, notes[0].midi)  # higher on screen
        self.assertLess(notes[1].midi, notes[2].midi)
        self.assertGreater(notes[3].midi, notes[2].midi)
        self.assertTrue(all(n.start == ctx.frame_times[4] for n in notes[1:]))

        f.table["plume"] = 0.0
        with patch.object(ctx, "frame_features", return_value=f):
            audio = mod.render(ctx)
        self.assertEqual(audio.shape, (ctx.n_samples, 2))
        self.assertFalse(np.any(audio))

    def test_living_earth_silence_and_screen_pan(self):
        names = ("co2_10_blood_flow", "co2_11_living_fluid", "co2_12_nervous_system")
        ctx = sonify.SonifyContext(5196, sonify.Timeline(["frame"] * 90, 30), sr=8000)
        table = pd.DataFrame({"plume": np.ones(90), "x": np.full(90, 0.1)})
        f = frames.FrameFeatures("orbit", table, np.zeros((90, frames.PROFILE_COLS)))
        for name in names:
            with self.subTest(name=name):
                mod = sonify.load(self.FOLDER / f"{name}.py")
                with patch.object(ctx, "frame_features", return_value=f):
                    left = mod.render(ctx)
                    f.table["x"] = 0.9
                    right = mod.render(ctx)
                    f.table["plume"] = 0.0
                    silent = mod.render(ctx)
                self.assertEqual(left.shape, (ctx.n_samples, 2))
                self.assertGreater(np.linalg.norm(left[:, 0]), np.linalg.norm(left[:, 1]))
                self.assertGreater(np.linalg.norm(right[:, 1]), np.linalg.norm(right[:, 0]))
                self.assertFalse(np.any(silent))
                f.table["plume"] = 1.0
                f.table["x"] = 0.1

    def test_lungs_follow_haze_not_orange_plume(self):
        mod = sonify.load(self.FOLDER / "co2_9_lungs.py")
        ctx = sonify.SonifyContext(5196, sonify.Timeline(["frame"] * 60, 30), sr=8000)
        haze = np.concatenate((np.linspace(0, 1, 30), np.linspace(1, 0, 30)))
        f = frames.FrameFeatures("orbit", pd.DataFrame({"haze": haze, "plume": np.zeros(60)}),
                                 np.zeros((60, frames.PROFILE_COLS)))
        with patch.object(ctx, "frame_features", return_value=f), \
             patch.object(sonify, "run", return_value=np.zeros((ctx.n_samples, 2))):
            audio = mod.render(ctx)
            self.assertGreater(np.max(np.abs(audio)), 0.1)
            np.testing.assert_allclose(audio[:, 0], audio[:, 1])

            def inhale_only(n, lo, hi, sr, seed):
                return np.ones(n) if seed == 91 else np.zeros(n)

            with patch.object(synth, "band_noise", side_effect=inhale_only):
                rising = mod.render(ctx)
            self.assertGreater(abs(rising[int(0.5 * ctx.sr), 0]), 0.1)
            self.assertAlmostEqual(rising[int(1.5 * ctx.sr), 0], 0.0)

            f.table["haze"] = 0.0
            f.table["plume"] = 1.0
            self.assertFalse(np.any(mod.render(ctx)))

    def test_lungs_mix_in_heartbeat(self):
        mod = sonify.load(self.FOLDER / "co2_9_lungs.py")
        ctx = sonify.SonifyContext(5196, sonify.Timeline(["frame"] * 120, 30), sr=8000)
        plume = 1 + np.sin(2 * np.pi * np.arange(120) / 24)
        f = frames.FrameFeatures("orbit", pd.DataFrame({
            "haze": np.ones(120), "plume": plume, "x": np.full(120, 0.5),
        }), np.zeros((120, frames.PROFILE_COLS)))
        with patch.object(ctx, "frame_features", return_value=f):
            heartbeat = sonify.run(self.FOLDER / "co2_13_heartbeat_improved.py", ctx)
            mixed = mod.render(ctx)
            with patch.object(sonify, "run", return_value=np.zeros_like(heartbeat)):
                breath = mod.render(ctx)
        self.assertGreater(np.max(np.abs(heartbeat)), 0.1)
        self.assertGreater(np.max(np.abs(mixed - breath)), 0.1)
        between_beats = np.max(np.abs(mixed[np.all(heartbeat == 0, axis=1)]))
        self.assertGreater(between_beats, 0.001)
        self.assertLess(between_beats, 0.1 * np.max(np.abs(mixed)))
        spectrum = np.abs(np.fft.rfft(breath[:, 0] * np.hanning(ctx.n_samples))) ** 2
        frequencies = np.fft.rfftfreq(ctx.n_samples, 1 / ctx.sr)
        self.assertLess(spectrum[frequencies > 1500].sum() / spectrum.sum(), 0.001)

    def test_needs_a_measured_movie(self):
        ctx = sonify.SonifyContext(5450, sonify.Timeline.linear(1880, 1889, 2, 30), movie="other.mp4")
        with self.assertRaises(LookupError):
            sonify.run(self.FOLDER / "co2_1_pulse_melody.py", ctx)


if __name__ == "__main__":
    unittest.main()
