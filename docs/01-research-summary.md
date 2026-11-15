# 01 — Research and project outcome

## Delivered product

EarthPod is a browser-based listening experience for selected NASA Earth visualizations. The deployed experience contains an introduction, a listening guide, two synchronized sonification chapters, a record page, and an accessibility statement:

- **The breathing planet:** NASA SVS 5196 global CO₂ visualization, 14 January–2 March 2020.
- **The night lights:** NASA SVS 5313 Earth-at-night visualization, 2012–2023.

The shipped scope is intentionally narrower than the early research concepts below. GISTEMP, Barcelona-region climate data, and other candidate datasets remain in the backend as reproducible research or demonstration work; they are not chapters in the production web app.

## Research that shaped the work

- The challenge centered on making Earth Information Center imagery available through sound as well as sight.
- Accessibility needed to be part of the interaction design: user-started audio, keyboard operation, captions, transcripts, and clear descriptions.
- Sonifications should explain how the source visualization informs the sound and avoid presenting visual patterns as calibrated physical measurements.
- The challenge's Resources tab provided the SVS pages for the backend's broader measurement and sonification experiments.

## Scope decisions

The initial proposal focused on GISTEMP, global temperature, and a Barcelona-region comparison. During implementation, the delivered web experience focused instead on two NASA SVS visualizations: CO₂ patterns and changing night lights. The earlier GISTEMP/player scripts remain useful for data validation and experimentation, but they are not part of the production chapter list.

Early notes about possible datasets, awards, rules, and event logistics were planning assumptions, not verified product claims. For current behavior and source attribution, use [the root README](../README.md), [data sources](02-data-sources.md), and [sonification design](03-sonification-design.md).
