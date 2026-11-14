"""SVS 5196 (DYAMOND global CO2) — technique: EARCONS.

Four short motifs to learn (5-10 minutes): they tell you *when* things happen, not how much.
Meant to be layered over another script (see co2_6_full_mix.py), but works alone as a calendar.
"""
import numpy as np

from jukebox import mapping

TITLE = "Calendar and pulse markers (earcons)"
DESCRIPTION = ("Four motifs. Tick (one soft low note): a new model day starts. Two rising notes: a new week "
               "(Monday). Three rising bells: a new month. Two falling plucks: the hour when that day's orange-red "
               "area (dense CO2) peaks, placed left or right where it is on screen - with an extra high bell when "
               "the peak is the biggest so far. Movies without a printed date get ticks every 24 frames and no "
               "week/month motifs. Data: date stamp and colours of the NASA SVS 5196 movie (GEOS / DYAMOND "
               "model, Jan-Mar 2020).")

D = mapping.TONIC_MIDI + 12      # D4
HALF_DAY = 12                    # frames (1 frame = 1 model hour)


def motif(t, midis, gap, dur, timbre, vel, pan=0.0, name="earcon"):
    return [mapping.Note(start=t + k * gap, dur=dur, midi=m, vel=vel, pan=pan, timbre=timbre,
                         voice=name, year=0, value=0.0) for k, m in enumerate(midis)]


def render(ctx):
    f = ctx.frame_features()
    t = ctx.frame_times
    plume, x = f.table.plume.to_numpy(), f.table.x.to_numpy()
    times = f.times                                           # datetimes, or None when the movie has no date
    day_starts = ([i for i, d in enumerate(times) if d.hour == 0] if times
                  else list(range(0, len(plume), 24)))

    notes = []
    for i in day_starts:
        if times and times[i].day == 1:
            notes += motif(float(t[i]), [D, D + 7, D + 12], 0.09, 0.9, "bell", 0.6, name="month")
        elif times and times[i].weekday() == 0:
            notes += motif(float(t[i]), [D, D + 5], 0.09, 0.25, "soft", 0.6, name="week")
        else:
            notes += motif(float(t[i]), [D - 12], 0, 0.12, "soft", 0.45, name="day")

    # daily peak = the highest hour within 12 hours either side (the pulse often straddles midnight UTC)
    best = None
    for i in range(HALF_DAY, len(plume) - HALF_DAY):
        if plume[i] <= 0 or plume[i] < plume[i - HALF_DAY:i + HALF_DAY + 1].max() or plume[i] == plume[i - 1]:
            continue
        pan = float(np.clip(4 * (x[i] - 0.5), -1, 1))
        notes += motif(float(t[i]), [D + 10, D + 7], 0.07, 0.2, "pluck", 0.7, pan, "peak")
        if best is not None and plume[i] > best:
            notes += motif(float(t[i]), [D + 24], 0, 1.2, "bell", 0.5, pan, "record")
        best = plume[i] if best is None else max(best, plume[i])
    return ctx.render_notes(notes, drone_midi=None)
