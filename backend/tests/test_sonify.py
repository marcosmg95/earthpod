import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from jukebox import frames, mapping, sonify, svs, synth


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

    def test_demo_script(self):
        ctx = sonify.SonifyContext(5450, sonify.Timeline.linear(1880, 1889, 2, 30))
        y = sonify.run(Path(__file__).resolve().parents[1] / "sonifications" / "gistemp_lead.py", ctx)
        self.assertEqual(y.shape, (ctx.n_samples, 2))
        self.assertGreater(abs(y).max(), 0.1)


class TestCo2Scripts(unittest.TestCase):
    """SVS 5196 scripts run on the committed frame features (data/derived/svs5196_*)."""
    MOVIE = "dyamondPointCloud_12-1-2023b_dyamond_co2_anim_globe_orbit_1080p30_h265.mp4"
    FOLDER = Path(__file__).resolve().parents[1] / "sonifications"

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
        scripts = {k: v for k, v in sonify.discover(self.FOLDER).items() if k.startswith("co2_")}
        self.assertEqual(len(scripts), 12)
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
            heartbeat = sonify.run(self.FOLDER / "co2_7_heartbeat.py", ctx)
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
