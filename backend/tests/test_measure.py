import io
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jukebox import frames, measure, nightlights_frames, pages, preview, sonify


class TestRegistry(unittest.TestCase):
    def test_every_measured_page_has_committed_results(self):
        known = measure.registry()
        self.assertEqual(set(known), {5196, 5313, *pages.PAGES})
        for viz_id, entry in known.items():
            with self.subTest(viz_id=viz_id):
                self.assertEqual(entry.viz_id, viz_id)
                self.assertTrue(entry.downloads and all(u.startswith("https://svs.gsfc.nasa.gov/") for u in
                                                        entry.downloads.values()))
                self.assertTrue(all(p.exists() for p in entry.outputs), "run python -m jukebox.measure")
                self.assertIsNotNone(sonify.measured_timeline(viz_id, entry.movie))
        self.assertIsNone(measure.page(5450))

    def test_raw_files_keep_their_old_places(self):
        self.assertEqual(list(measure.page(5313).downloads), [nightlights_frames.RAW_PATH])
        self.assertEqual(measure.page(4960).downloads.keys(),
                         {pages.raw_path(4960), pages.raw_path(4960).with_name("atmos_river_DATE_ONLY_HD.mp4")})
        self.assertTrue(all(p.parent.name == "svs5196" for p in measure.page(5196).downloads))

    def test_resolve_movie(self):
        co2 = measure.page(5196)
        self.assertEqual(co2.resolve(None), frames.MOVIES["orbit"])
        self.assertEqual(co2.resolve("zoom"), frames.MOVIES["zoom"])                  # name, not a substring
        self.assertEqual(co2.resolve("zoomwest"), frames.MOVIES["zoomwest"])
        self.assertEqual(co2.resolve(frames.MOVIES["tilt"]), frames.MOVIES["tilt"])
        self.assertEqual(co2.resolve("3x3hyperwall"), frames.MOVIES["zoomwest"])      # unique part of a filename
        for bad in ("globe", "nope"):
            with self.assertRaises(ValueError):
                co2.resolve(bad)
        self.assertEqual(preview.build_context(5196, "tilt").movie, frames.MOVIES["tilt"])


class TestPipeline(unittest.TestCase):
    def test_downloads_only_what_is_missing_then_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            have, missing = Path(tmp) / "have.mp4", Path(tmp) / "missing.mp4"
            have.write_bytes(b"x")
            got = []
            entry = measure.MeasuredPage(1, {"movie": "have.mp4"}, {have: "https://a/have", missing: "https://a/m"},
                                         lambda: "measured", ())
            with redirect_stdout(io.StringIO()):
                self.assertEqual(measure.measure(entry, download=lambda url, path: got.append((url, path))),
                                 "measured")
        self.assertEqual(got, [("https://a/m", missing)])

    def test_command_line(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(measure.main(["--list", "5669", "5313"]), 0)
        self.assertRegex(out.getvalue(), r"SVS 5669: [01]/1 raw files present")      # raw/ is not in git
        self.assertIn("svs5313_eic_grids.npz", out.getvalue())
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            measure.main(["5450"])


class TestPageContract(unittest.TestCase):
    def test_real_pages_follow_it(self):
        for viz_id in pages.PAGES:
            self.assertIs(pages.module(viz_id), pages.check(pages.module(viz_id)))

    def test_broken_module_says_what_is_wrong(self):
        mod = types.ModuleType("jukebox.pages.svs1")
        mod.MOVIE, mod.FPS, mod.NOTES, mod.EXTRA = "a.mp4", "30", "notes", ["b.mp4"]
        mod.extract = lambda path: None
        with self.assertRaises(TypeError) as e:
            pages.check(mod)
        for problem in ("URL must be a str", "FPS must be a number", "labels() is missing", "EXTRA must be a dict"):
            self.assertIn(problem, str(e.exception))


if __name__ == "__main__":
    unittest.main()
