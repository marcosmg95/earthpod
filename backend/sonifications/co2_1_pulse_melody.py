"""SVS 5196 (DYAMOND global CO2) — technique: PARAMETER MAPPING (PMSon).

Only two sound traits carry data, because traits interact: pitch = how much dense CO2 is on
screen, left/right = where it is. Loudness and tempo stay fixed.
"""
import numpy as np

from jukebox import mapping

TITLE = "CO2 pulse melody (parameter mapping)"
DESCRIPTION = ("Six plucked notes per model day (one per 4 hours): the more of the picture is orange-red "
               "(dense CO2), the higher the note on a D minor pentatonic scale; the low drone is 'no orange "
               "on screen' and the movie's maximum sits three octaves above it. Left/right follows where the "
               "orange is on screen. A slow string plays each day's tan haze (medium CO2). You hear the daily "
               "pulse as a rising and falling figure. Data: colours measured from the NASA SVS 5196 movie "
               "(GEOS / DYAMOND model, Jan-Mar 2020) - an index of the picture, not ppm.")

HOURS_PER_NOTE = 4      # movie frames per melody note (1 frame = 1 model hour)
STEPS_AT_MAX = 15       # scale steps between "nothing" and the movie's maximum (15 = three octaves)


def render(ctx):
    f = ctx.frame_features()
    t = ctx.frame_times
    plume, haze, x = (f.table[c].to_numpy() for c in ("plume", "haze", "x"))
    lead = mapping.Voice("Dense CO2", "plume", plume.max() / STEPS_AT_MAX, mapping.TONIC_MIDI, 0.0, "pluck", 0.9)
    pad = mapping.Voice("Haze", "haze", (haze.max() - haze.min()) / 10, mapping.TONIC_MIDI - 12, 0.0, "string", 0.3)
    step_s = HOURS_PER_NOTE / ctx.timeline.fps

    notes = []
    for i in range(0, len(plume), HOURS_PER_NOTE):
        value = float(plume[i:i + HOURS_PER_NOTE].mean())
        notes.append(mapping.Note(
            start=float(t[i]), dur=step_s * 1.5, midi=mapping.value_to_midi(value, lead.step_c, lead.tonic_midi),
            vel=lead.gain, pan=float(np.clip(4 * (x[i:i + HOURS_PER_NOTE].mean() - 0.5), -1, 1)),
            timbre=lead.timbre, voice=lead.name, year=i, value=value))            # year = frame number here
    for i in range(0, len(haze), 24):                                             # one string note per day
        value = float(haze[i:i + 24].mean() - haze.min())
        notes.append(mapping.Note(
            start=float(t[i]), dur=24 / ctx.timeline.fps * 1.2, midi=mapping.value_to_midi(value, pad.step_c, pad.tonic_midi),
            vel=pad.gain, pan=0.0, timbre=pad.timbre, voice=pad.name, year=i, value=value))
    return ctx.render_notes(notes)                                                # + drone = no orange
