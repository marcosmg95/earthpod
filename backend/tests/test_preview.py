import tempfile
import unittest
from pathlib import Path

import numpy as np

from jukebox import preview, sonify

SCRIPT = """import numpy as np
TITLE = "t"
GAIN = 0.5
STEPS = 3
PARAMS = {"GAIN": (0.0, 1.0), "STEPS": (1, 9)}
def render(ctx):
    return np.full(ctx.n_samples, GAIN * STEPS)
"""


def make_root(tmp: str) -> Path:
    root = Path(tmp)
    (root / "svs1").mkdir()
    (root / "svs1" / "demo_1_a.py").write_text(SCRIPT)
    (root / "svs1" / "demo_10_b.py").write_text(SCRIPT)
    return root


class TestParams(unittest.TestCase):
    def test_declared_params_and_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_root(tmp) / "svs1" / "demo_1_a.py"
            specs = sonify.params_of(sonify.load(path))
            self.assertEqual((specs["GAIN"].default, specs["GAIN"].hi), (0.5, 1.0))
            self.assertEqual(specs["STEPS"].step, 1)
            ctx = sonify.SonifyContext(1, sonify.Timeline(["2000"] * 4, fps=2), params={"GAIN": "0.1", "STEPS": 2.4, "X": 9})
            self.assertAlmostEqual(sonify.run(path, ctx)[0, 0], 0.2)       # 0.1 * int(2.4)
            ctx.params = {}
            self.assertAlmostEqual(sonify.run(path, ctx)[0, 0], 1.0)       # 0.5 * 3 = 1.5, clipped

    def test_missing_constant_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.py"
            p.write_text('PARAMS = {"NOPE": (0, 1)}\ndef render(ctx):\n    return 0\n')
            with self.assertRaises(AttributeError):
                sonify.params_of(sonify.load(p))

    def test_parse_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs = sonify.params_of(sonify.load(make_root(tmp) / "svs1" / "demo_1_a.py"))
        self.assertEqual(preview.parse_overrides(["GAIN=0.25", "STEPS=4.0"], specs), {"GAIN": 0.25, "STEPS": 4})
        with self.assertRaises(ValueError):
            preview.parse_overrides(["NOPE=1"], specs)
        with self.assertRaises(ValueError):
            preview.parse_overrides(["GAIN"], specs)


class TestFindScript(unittest.TestCase):
    def test_name_prefix_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            self.assertEqual(preview.find_script("demo_1", root).name, "demo_1_a.py")     # not demo_10
            self.assertEqual(preview.find_script("svs1/demo_10", root).name, "demo_10_b.py")
            self.assertEqual(preview.find_script(str(root / "svs1" / "demo_1_a.py")).name, "demo_1_a.py")
            with self.assertRaises(ValueError):
                preview.find_script("demo", root)
            with self.assertRaises(ValueError):
                preview.find_script("nothing", root)
            self.assertEqual(preview.viz_id_of(root / "svs1" / "demo_1_a.py"), 1)


class TestWindow(unittest.TestCase):
    def test_cut_fades_inner_edges_only(self):
        y = np.ones((1000, 2))
        mid = preview.cut(y, 100, 2.0, 8.0)
        self.assertEqual(mid.shape, (600, 2))
        self.assertEqual((mid[0, 0], mid[-1, 0], mid[300, 0]), (0.0, 0.0, 1.0))
        whole = preview.cut(y, 100, 0.0, 10.0)
        self.assertEqual((whole[0, 0], whole[-1, 0]), (1.0, 1.0))                     # movie edges untouched

    def test_co2_context_and_window_text(self):
        ctx = preview.build_context(5196)
        self.assertEqual(len(ctx.frame_features().table), len(ctx.timeline.labels))
        self.assertIn("frames 30-59", preview.describe_window(ctx, 1.0, 2.0))

    def test_main_writes_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, preview.OUT_DIR = preview.OUT_DIR, Path(tmp)
            try:
                script = Path(__file__).parents[1] / "sonifications" / "svs5196" / "co2_15_lungs_heart_region.py"
                self.assertEqual(preview.main([str(script), "--start", "1", "--end", "3", "--no-play",
                                               "--set", "BREATH_GAIN=0.1"]), 0)
                wav = (Path(tmp) / script.with_suffix(".wav").name).read_bytes()
            finally:
                preview.OUT_DIR = old
        self.assertEqual(wav[:4], b"RIFF")
        self.assertGreater(len(wav), 2 * 44100 * 4 * 0.9)                             # 2 s stereo 16-bit


if __name__ == "__main__":
    unittest.main()
