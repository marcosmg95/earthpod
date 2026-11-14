"""Tests for the 'Earth in layers' track (temperature + night lights, shared years only)."""
import unittest

import numpy as np
import pandas as pd


from jukebox import mapping


def sample():
    years = range(2008, 2016)
    temp = pd.DataFrame({"global": [0.5, 0.6, 0.7, 0.6, 0.65, 0.8, 0.75, 0.9],
                         "barcelona": [1.0, 0.9, 1.1, 1.0, 1.2, 1.1, 1.3, np.nan]}, index=years)
    night = pd.DataFrame({"barcelona": [0.0, -2.0, -4.0, -5.0, -6.0],
                          "kyiv": [0.0, 3.0, -40.0, -38.0, -35.0]}, index=range(2012, 2017))
    return temp, night


class TestLayersTrack(unittest.TestCase):
    def setUp(self):
        self.t = mapping.build_layers_track(*sample())
        self.years = self.t["years"]

    def test_only_shared_years(self):
        # night starts 2012, Barcelona temperature is missing in 2015, night ends 2016 -> 2012-2014
        self.assertEqual([y["year"] for y in self.years], [2012, 2013, 2014])
        self.assertEqual(self.t["name"], "Earth in layers (2012–2014)")

    def test_every_year_has_every_layer(self):
        names = {v.name for v in mapping.LAYER_VOICES}
        for y in self.years:
            self.assertEqual(set(y["values"]), names)
            self.assertEqual(set(y["midi"]), names)

    def test_home_notes(self):
        m = self.years[0]["midi"]
        self.assertEqual(m["Barcelona lights"], mapping.NIGHT_TONIC_MIDI)   # 2012 glow = home note
        self.assertEqual(m["Kyiv lights"], mapping.NIGHT_TONIC_MIDI + 12)

    def test_events(self):
        y = {d["year"]: d for d in self.years}
        self.assertTrue(y[2014]["dissonant"])                 # Kyiv 103% -> 60% of 2012 light: -42% in a year
        self.assertIn("Kyiv lost 42%", y[2014]["description"])
        self.assertFalse(y[2012]["record"])                   # 0.65 < 0.7 (2010): records use full history
        self.assertTrue(y[2013]["record"])
        self.assertIn("Barcelona region", self.t["events"][0]["text"])  # 2012: 1.2 beats 1.1 (2010)
        self.assertEqual([e["year"] for e in self.t["events"]], [2012, 2013, 2014])

    def test_no_shared_years(self):
        temp, night = sample()
        with self.assertRaises(ValueError):
            mapping.build_layers_track(temp.loc[:2010], night)


if __name__ == "__main__":
    unittest.main()
