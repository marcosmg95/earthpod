"""SVS 5196 (DYAMOND global CO2) — screen position and spread as a moving chord."""
import numpy as np

from jukebox import mapping

TITLE = "CO2 currents (screen position and spread)"
DESCRIPTION = ("Every four frames, a soft chord follows the orange-red area: higher on screen means higher "
               "pitch, left/right follows its screen position, and a wider horizontal spread makes a wider "
               "chord. No orange at a sampled frame means silence for that interval. Data: colours measured "
               "from the NASA SVS 5196 movie (GEOS / DYAMOND model) - picture indices, not ppm, altitude "
               "or wind; camera movement and background colours also affect them.")

FRAMES_PER_CHORD = 4
HEIGHT_STEPS = 10
MAX_SPREAD_STEPS = 5
SPREAD_AT_MAX = 0.25  # weighted horizontal standard deviation, as a fraction of screen width


def notes_for(f, frame_times, fps):
    columns = np.linspace(0, 1, f.profiles.shape[1])
    notes = []
    for i in range(0, len(f.table), FRAMES_PER_CHORD):
        row = f.table.iloc[i]
        profile = f.profiles[i]
        total = profile.sum()
        if row.plume <= 0 or total <= 0:
            continue
        mean = float(np.dot(profile, columns) / total)
        spread = float(np.sqrt(np.dot(profile, (columns - mean) ** 2) / total))
        width = int(np.round(MAX_SPREAD_STEPS * np.clip(spread / SPREAD_AT_MAX, 0, 1)))
        height = int(np.round(HEIGHT_STEPS * (1 - np.clip(row.y, 0, 1))))
        pan = float(np.clip(2 * row.x - 1, -1, 1))
        degrees = [height] if width == 0 else [height - width, height, height + width]
        for degree in degrees:
            notes.append(mapping.Note(
                start=float(frame_times[i]), dur=FRAMES_PER_CHORD / fps,
                midi=mapping.degree_to_midi(degree, mapping.TONIC_MIDI + 12),
                vel=0.6 / len(degrees), pan=pan, timbre="soft",
                voice="CO2 currents", year=i, value=spread,
            ))
    return notes


def render(ctx):
    notes = notes_for(ctx.frame_features(), ctx.frame_times, ctx.timeline.fps)
    return ctx.render_notes(notes, drone_midi=None)
