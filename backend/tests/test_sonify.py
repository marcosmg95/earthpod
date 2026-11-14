import tempfile
import unittest
from pathlib import Path

import pandas as pd

from jukebox import mapping, sonify, svs, synth


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


if __name__ == "__main__":
    unittest.main()
