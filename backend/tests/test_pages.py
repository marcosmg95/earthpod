"""jukebox.pages: per-page frame measurements of the challenge's SVS pages, and the scripts that use them."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from jukebox import pages, preview, sonify
from jukebox.pages import svs4960, svs5011, svs5533, svs5669

SONIFICATIONS = Path(__file__).resolve().parents[1] / "sonifications"


class TestHelpers(unittest.TestCase):
    def test_lon_label(self):
        self.assertEqual(pages.lon_label(-122.3), "120°W")
        self.assertEqual(pages.lon_label(2.0), "0°")
        self.assertEqual(pages.lon_label(179.9), "180°")
        self.assertEqual(pages.lon_label(-179.9), "180°")
        self.assertEqual(pages.lon_label(47.6), "50°E")

    def test_block_mean_and_centroid(self):
        a = np.zeros((4, 6))
        a[:, 4:] = 1.0
        np.testing.assert_allclose(pages.block_mean(a, 2, 3), [[0, 0, 1], [0, 0, 1]])
        self.assertAlmostEqual(pages.centroid(a, axis=1), (4.5 + 5.5) / 2 / 6)
        self.assertEqual(pages.centroid(np.zeros((3, 3)), axis=0), 0.5)

    def test_per_sample_holds_each_frame(self):
        f = pages.PageFeatures(1, "m", 10.0, False, pd.DataFrame({"label": ["a"] * 3, "v": [0.0, 1.0, 0.0]}), {}, [])
        y = f.column("v", 300, 100)                      # 3 s at 100 Hz, 1 frame = 10 samples
        self.assertAlmostEqual(y[15], 1.0)               # middle of frame 1
        self.assertAlmostEqual(y[5], 0.0)
        self.assertEqual(f.duration, 0.3)


class TestRegistryAndFiles(unittest.TestCase):
    def test_every_page_module_follows_the_contract(self):
        for viz_id in pages.PAGES:
            mod = pages.module(viz_id)
            for name in ("MOVIE", "URL", "FPS", "NOTES", "labels", "extract"):
                self.assertTrue(hasattr(mod, name), f"svs{viz_id} lacks {name}")
            self.assertTrue(mod.URL.endswith(mod.MOVIE))
            self.assertIs(pages.spec_for(viz_id, mod.MOVIE), mod)
            self.assertIsNone(pages.spec_for(viz_id, "other.mp4"))
        self.assertIsNone(pages.module(5313))

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(pages, "DERIVED_DIR", Path(tmp)):
            table = pd.DataFrame({"lon": [-170.0, 10.0]})
            pages.save(5669, table, {"dust": np.array([[0.0, 0.5], [1.0, 0.25]]), "raw": np.array([2.0, -1.0])})
            f = pages.load(5669, svs5669.MOVIE)
        self.assertEqual(f.labels, ["170°W", "10°E"])
        self.assertTrue(f.still)
        np.testing.assert_allclose(f.arrays["dust"], [[0.0, 0.5], [1.0, 0.25]], atol=1 / 255)
        np.testing.assert_allclose(f.arrays["raw"], [2.0, -1.0])        # not 0..1: stored as float
        self.assertEqual(f.chapter_times()[0][0], "Americas")

    def test_committed_measurements_match_their_timelines(self):
        for viz_id in pages.PAGES:
            mod = pages.module(viz_id)
            f = pages.load(viz_id, mod.MOVIE)
            self.assertIsNotNone(f, f"run scripts/poc8_page_features.py {viz_id}")
            self.assertEqual(len(f.labels), f.n_frames)
            self.assertLessEqual(f.duration, sonify.MAX_DURATION_S)
            for name, a in f.arrays.items():
                self.assertEqual(len(a), f.n_frames, f"svs{viz_id} {name}")
                self.assertTrue(np.isfinite(a).all())
            for title, t in f.chapter_times():
                self.assertLess(t, f.duration, f"svs{viz_id} chapter {title}")


class TestMeasurements(unittest.TestCase):
    def test_aerosol_colours(self):
        legend = {"black_carbon": (70, 95, 210), "dust": (220, 155, 195), "sea_salt": (170, 170, 130),
                  "sulfate": (50, 220, 80)}                            # BGR of the legend swatches
        for name, bgr in legend.items():
            px = np.array([[bgr]], dtype=np.uint8)
            got = {k: float(v[0, 0]) for k, v in svs5669.layers(px).items()}
            self.assertEqual(max(got, key=got.get), name, got)
            self.assertGreater(got[name], 0.3)
        dark = svs5669.layers(np.full((1, 1, 3), 20, np.uint8))
        self.assertFalse(any(v.any() for v in dark.values()))

    def test_air_quality_panels_split_by_order(self):
        # ... O3 | orange run of 2.5 panels | NOx ...: the last panel width next to NOx is PM2.5
        kind = np.array([3] * 10 + [0] * 25 + [2] * 10)
        out = svs5533.split_orange(kind, np.full((1, 45), 0.5), panel=10)
        self.assertEqual("".join("?CPNO"[k + 1] for k in out), "O" * 10 + "C" * 15 + "P" * 10 + "N" * 10)
        edge = svs5533.split_orange(np.array([0] * 6 + [2] * 4), np.full((1, 10), 0.5), panel=10)
        self.assertTrue((edge[:6] == 1).all())                          # cut at the screen edge: all PM2.5

    def test_air_quality_labels(self):
        self.assertEqual(svs5533.labels(pd.DataFrame({"centre": ["o3", "nox"]})),
                         ["centre: ozone", "centre: nitrogen oxides"])

    def test_atmospheric_river_dates_are_read_from_glyphs(self):
        reps, names = svs4960._templates()
        y0, y1, x0, _ = svs4960.TEXT
        gray = np.zeros((1080, 1920), np.uint8)
        x = x0 + 20
        for ch in "Dec11201018:43".replace(" ", ""):
            g = (reps[names.index(ch)] * 255).astype(np.uint8)
            big = np.kron(g, np.ones((3, 3), np.uint8))                 # 48 x 72 px glyph
            gray[y0 + 6:y0 + 6 + big.shape[0], x:x + big.shape[1]] = big
            x += big.shape[1] + 12
        days = svs4960.read_date(gray)
        self.assertAlmostEqual(days, (pd.Timestamp("2010-12-11 18:43") - pd.Timestamp("2010-10-01")).total_seconds()
                               / 86400, places=6)
        self.assertEqual(svs4960.read_date(np.zeros((1080, 1920), np.uint8)), -1.0)
        self.assertEqual(svs4960.labels(pd.DataFrame({"day": [71.78, -1.0]})), ["11 Dec 2010 18h", "—"])

    def test_lightning_seasons(self):
        t = pd.DataFrame({"north": [0.9] * 70 + [0.1] * 70, "flashes": [0.01] * 140})
        lab = svs5011.labels(t)
        self.assertEqual((lab[0], lab[-1]), ("northern storm season", "southern storm season"))
        self.assertEqual(svs5011.season(0.5, 0.0), "few storms on the map")


class TestContextAndScripts(unittest.TestCase):
    def test_sample_rate_drops_for_long_movies(self):
        self.assertEqual(sonify.sample_rate_for(60), 44100)
        self.assertEqual(sonify.sample_rate_for(300), sonify.LONG_SR)

    def test_page_features_need_the_measured_timeline(self):
        ctx = sonify.SonifyContext(5669, sonify.Timeline(["x"] * 480, 10.0), movie=svs5669.MOVIE)
        self.assertEqual(ctx.page_features().n_frames, 480)
        ctx.timeline = sonify.Timeline(["x"] * 480, 30.0)
        with self.assertRaises(ValueError):
            ctx.page_features()
        ctx.movie = "other.png"
        with self.assertRaises(LookupError):
            ctx.page_features()

    def test_preview_builds_page_contexts(self):
        ctx = preview.build_context(5425)
        self.assertEqual(ctx.movie, pages.module(5425).MOVIE)
        self.assertEqual(ctx.sr, sonify.LONG_SR)                       # 317 s movie
        self.assertEqual(preview.build_context(5669).sr, 44100)

    def test_every_page_script_renders_its_stems(self):
        for viz_id in pages.PAGES:
            scripts = sonify.discover(sonify.folder_for(SONIFICATIONS, viz_id))
            self.assertTrue(scripts, f"no script for SVS {viz_id}")
            for name, path in scripts.items():
                with self.subTest(script=name):
                    ctx = preview.build_context(viz_id)
                    ctx.sr = 8000
                    stems = sonify.render_stems(path, ctx)
                    mod = sonify.load(path)
                    self.assertEqual(set(stems.audio), set(getattr(mod, "STEMS", {"mix": None})))
                    for stem, a in stems.audio.items():
                        self.assertEqual(a.shape, (ctx.n_samples, 2), stem)
                        self.assertTrue(np.isfinite(a).all(), stem)
                    mix = stems.mix()
                    self.assertGreater(np.abs(mix).max(), 0.1)
                    self.assertTrue(getattr(mod, "TITLE", "") and getattr(mod, "DESCRIPTION", ""))


if __name__ == "__main__":
    unittest.main()
