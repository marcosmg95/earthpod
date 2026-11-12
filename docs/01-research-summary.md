# 01 — Research summary (10 Nov 2026)

## Bottom line
- Build a static web app (Tone.js + Canvas) that plays SVS Global Temperature Anomalies frames (SVS 5450/5603) with music driven by GISTEMP v4 numbers.
- Add a Barcelona-region track (GISTEMP 2° grid cell ~41.4°N, 2.2°E) for the social/local angle.
- Accessibility is not a feature, it's the product: keyboard-only, live-region narration, reference tone, orientation intro, transcripts.

## Why this angle
- At least ~12 public GitHub repos already target this exact challenge, mostly "colors → instruments" or "3D globe + synth". Visual flash won't stand out.
- Colormaps are perceptual, not linear: mapping raw pixel colour to notes doesn't follow the data. Real values (or colorbar-inverted pixels validated against GISTEMP) do.
- Precedent: team Arcobaleno won the 2023 Global Connection Award with a sonification project for blind users; SongSAT won "Most Inspirational" in 2018 (image → music).

## Judging criteria
Impact · Creativity · Validity · Relevance · Presentation. Local events nominate to Global Judging (nominees Dec 2026, winners Jan 2027).

## Unknowns (resolve Fri 13 Nov)
- Official challenge Resources tab — published Fri 13 Nov. Switch to named datasets if any (Relevance).
- Project Submission Guide + Judging guide — published Fri 13 Nov (video length, required fields).
- AI policy wording (possibly renamed "Super Intelligence (SI)" tools in 2026 FAQ; unconfirmed). Disclosure of AI use is required either way.
- Whether code must be written during the event (one third-party page claims so; unverified).

## Caveats
- Some SVS IDs (sea ice, CO₂, sea level, 4626 colorbars) come from search snippets, not verified pages.
- A single 2° grid cell is coarse: call it "the Barcelona region".
