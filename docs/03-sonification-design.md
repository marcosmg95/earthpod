# 03 — Sonification design

## Design principle

Make the relationship between the source visualization and its sound understandable. EarthPod's chapter sonifications use features measured from the selected visualizations; they are artistic interpretations of those pictures, not substitutes for the underlying scientific datasets.

## Shipped chapters

### The breathing planet

The chapter uses NASA SVS 5196's global CO₂ visualization. Its sound follows picture features such as the visible orange-red area, position, and tan haze. Heartbeat and breathing sounds are metaphors for visual patterns; they do not represent human physiology or calibrated atmospheric CO₂ concentrations.

### The night lights

The chapter uses NASA SVS 5313's 2012–2023 Earth-at-night visualization. It moves through the yearly maps and change map, where the source visualization uses purple for new lights and orange for lights that dimmed. Sound follows image features and the visualization's sequence; the measurements are not calibrated radiance values or city-level measurements.

The center label, legends, map details, transitions, and zooms can affect image-derived features. They should be understood as visual indices with the limitations described in [the backend guide](../backend/README.md), not as independent measurements of Earth-system variables.

## Interpretability and accessibility

- The listening guide introduces the sound and its controls before the chapters.
- Chapters provide captions, a sound chart, and available time-coded descriptions and transcripts.
- Playback begins only after the user activates it; the player exposes keyboard-operable controls.
- Where a chapter has no spoken descriptions for a moment, the transcript may be empty for that moment. See the [accessibility statement](04-accessibility.md).

## Other research mappings

The repository also contains GISTEMP-based sonification work and exploratory scripts for other NASA SVS pages. These are backend experiments and demos, not additional chapters in the production web app. Detailed implementation notes and reproduction commands are in [backend/README.md](../backend/README.md).

## Credits

The source visualizations are credited to NASA Scientific Visualization Studio (SVS 5196 and SVS 5313). EarthPod is not endorsed by NASA. See [data sources](02-data-sources.md) for citations and source limitations.
