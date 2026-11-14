"""Demo sonification: the jukebox lead melody, locked to the movie's own years.

Best with SVS 5450 (GISTEMP map, time.txt gives one year per frame, 1880-2024).
Copy this file to start a new script; see the contract in src/jukebox/sonify.py.
"""
from jukebox import data, mapping

TITLE = "GISTEMP lead melody"
DESCRIPTION = ("One note each time a new year appears on screen; +0.1 °C = one step up a D minor "
               "pentatonic scale; the low drone is 0 °C (1951-1980 average). Data: NASA GISS GISTEMP v4.")


def render(ctx):
    lead = mapping.DEFAULT_VOICES[0]                     # "Global", 0.1 °C per step, pluck
    notes = ctx.notes_from_series(data.load_global_annual(), lead)
    return ctx.render_notes(notes)                       # + 0 °C reference drone
