"""Run from backend/:  uv run python -m unittest discover -s tests -v"""
import unittest


import numpy as np

from jukebox import colormap, data, mapping, synth


class TestData(unittest.TestCase):
    def test_global_annual(self):
        g = data.load_global_annual()
        self.assertEqual(g.index.min(), 1880)
        self.assertAlmostEqual(g.loc[2024], 1.28)
        self.assertTrue(g.isna().sum() == 0)

    def test_zonal(self):
        z = data.load_zonal_annual()
        for col in data.ZONES:
            self.assertIn(col, z.columns)


class TestMapping(unittest.TestCase):
    def test_zero_is_tonic(self):
        self.assertEqual(mapping.value_to_midi(0.0, 0.1, mapping.TONIC_MIDI), mapping.TONIC_MIDI)

    def test_monotonic(self):
        vals = np.linspace(-0.6, 1.6, 50)
        m = [mapping.value_to_midi(v, 0.1, mapping.TONIC_MIDI) for v in vals]
        self.assertTrue(all(b >= a for a, b in zip(m, m[1:])))

    def test_score(self):
        df = data.load_zonal_annual()[list(data.ZONES)]
        df["global"] = data.load_global_annual()
        notes, info, dur = mapping.build_score(df)
        self.assertGreater(dur, 30)
        self.assertTrue(info[-1].year >= 2025)
        self.assertIn(2024, [y.year for y in info if y.record])
        arctic = [y.midi["Arctic"] for y in info if y.year == 2024][0]
        self.assertEqual(arctic, max(info[-2].midi.values()))  # Arctic is the highest voice in 2024


class TestSynth(unittest.TestCase):
    def test_render(self):
        n = [mapping.Note(0, 0.5, 62, 1, 0, "pluck", "x", 2000, 0.0),
             mapping.Note(0.2, 1.0, 74, 1, 0, "bell", "x", 2000, 0.0)]
        y = synth.render(n, 1.0, sr=8000, tail=0.5)
        self.assertEqual(y.shape[1], 2)
        self.assertAlmostEqual(np.abs(y).max(), 10 ** (-6 / 20), places=3)


class TestColormap(unittest.TestCase):
    def test_round_trip(self):
        """Encode a known field with a colormap, draw a colorbar image, invert, compare."""
        import matplotlib
        cmap = matplotlib.colormaps["RdBu_r"]
        bar = (np.array([cmap(x)[:3] for x in np.linspace(0, 1, 600)]) * 255).astype(np.uint8)
        img = np.full((60, 700, 3), 255, np.uint8)
        img[20:40, 50:650] = bar[None, :, :]
        lut, t = colormap.lut_from_colorbar(img)
        rng = np.random.default_rng(0)
        truth = np.clip(rng.normal(0.6, 0.15, (90, 180)), 0, 1)
        frame = (cmap(truth)[..., :3] * 255).astype(np.uint8)
        frame[:5] = (0, 0, 0)  # a black border/label band that must be rejected
        got = colormap.invert(frame, lut, t, max_de=12)
        self.assertTrue(np.isnan(got[:5]).all())
        err = np.nanmean(np.abs(got[5:] - truth[5:]))
        self.assertLess(err, 0.02)
        self.assertAlmostEqual(colormap.area_mean(got), colormap.area_mean(np.where(np.isnan(got), np.nan, truth)), places=2)


if __name__ == "__main__":
    unittest.main()
