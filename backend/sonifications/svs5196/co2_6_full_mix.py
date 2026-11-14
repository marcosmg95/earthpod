"""SVS 5196 (DYAMOND global CO2) — three techniques layered: parameter mapping + earcons + auditory icons.

Each layer is one of the other scripts in this folder, so edit those (or the gains below) and re-render.
"""
from pathlib import Path

import numpy as np

from jukebox import sonify, synth

TITLE = "Full mix: melody + markers + breath"
DESCRIPTION = ("The pulse melody (pitch = how much dense CO2 is on screen, left/right = where), the calendar "
               "earcons (day tick, week, month, daily peak, record bell) and, quietly underneath, the breath / "
               "fire / wind icons. Data: colours and date stamp measured from the NASA SVS 5196 movie "
               "(GEOS / DYAMOND model, Jan-Mar 2020) - an index of the picture, not ppm.")

LAYERS = {                      # script name -> gain
    "co2_1_pulse_melody": 1.0,
    "co2_3_calendar_earcons": 0.6,
    "co2_2_breath_and_fire": 0.3,
}


def render(ctx):
    out = np.zeros((ctx.n_samples, 2))
    for name, gain in LAYERS.items():
        out += gain * sonify.run(Path(__file__).with_name(f"{name}.py"), ctx)
    return synth.normalize(out)
