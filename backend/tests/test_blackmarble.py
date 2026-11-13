"""Geometry tests for jukebox.blackmarble (no HDF5 files or h5py needed)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jukebox import blackmarble as bm  # noqa: E402


class TestBlackMarble(unittest.TestCase):
    def test_tiles(self):
        self.assertEqual(bm.REGIONS["barcelona"].tile, "h18v04")
        self.assertEqual(bm.REGIONS["kyiv"].tile, "h21v03")
        self.assertEqual(bm.REGIONS["delhi"].tile, "h25v06")
        self.assertEqual(bm.tile_origin("h18v04"), (50.0, 0.0))

    def test_window(self):
        rows, cols = bm.pixel_window(bm.REGIONS["barcelona"], "h18v04", 2400, 2400)
        # 15 arc-sec pixels: lat 41.60 -> row 2016, 41.25 -> 2100; lon 1.90 -> col 456, 2.35 -> 564
        self.assertEqual((rows.start, rows.stop), (2016, 2100))
        self.assertEqual((cols.start, cols.stop), (456, 564))
        with self.assertRaises(ValueError):
            bm.pixel_window(bm.REGIONS["kyiv"], "h18v04", 2400, 2400)

    def test_parse_name(self):
        p = Path("VNP46A4.A2012001.h18v04.002.2025086171531.h5")
        self.assertEqual(bm.parse_name(p), (2012, "h18v04"))


class TestNightTrack(unittest.TestCase):
    def test_build(self):
        import pandas as pd
        from jukebox import mapping
        pct = pd.DataFrame({"barcelona": [0.0, -4.0, -10.0], "kyiv": [0.0, 2.0, -40.0]},
                           index=[2012, 2013, 2014])
        t = mapping.build_night_track(pct)
        y = t["years"]
        self.assertEqual(y[0]["midi"], {"Barcelona": 62, "Kyiv": 74})   # 2012 = home note
        self.assertLess(y[2]["midi"]["Barcelona"], y[1]["midi"]["Barcelona"])
        self.assertFalse(y[1]["dissonant"])
        self.assertTrue(y[2]["dissonant"])                                # Kyiv lost >20% in a year
        self.assertIn("Kyiv lost", y[2]["description"])
        self.assertEqual(t["duration_s"], 3.0)


if __name__ == "__main__":
    unittest.main()
