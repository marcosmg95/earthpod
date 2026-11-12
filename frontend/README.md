# frontend/

Static web apps, no build step. Serve a folder with `python -m http.server` and open it in a browser.

| Folder | What it is |
|---|---|
| `arcade/` | **Earth Jukebox arcade** (the experience): scroll story → insert coin → a NASA Earth picture played as chiptune |
| `player/` | Keyboard-first, screen-reader-friendly GISTEMP player (vanilla Web Audio). Reads `tracks.json` and `frames/` |

## Arcade
```powershell
python backend\scripts\fetch_arcade_images.py        # ~34 public-domain NASA images -> frontend\arcade\images + manifest.json
python backend\scripts\make_voice.py                 # voice-over clips (Windows TTS + 80s effect) -> frontend\arcade\voice\*.wav
cd frontend\arcade; python -m http.server 8000          # open http://localhost:8000  (?debug logs the score, ?debug&coin skips to the track)
```
Image -> sound (all knobs in `frontend/arcade/sonify.js` `MAPPING`): the picture is scanned left to right, 64 columns;
row height = pitch (D minor pentatonic), brightness = volume (dark = silent), colour = instrument
(the four elements: WATER blue = triangle, LAND green/brown = pulse, FIRE red/yellow = square, WIND white/grey = noise),
bright columns play faster, stereo pans with the scan. The image starts as the exact 64-column grid being played
and sharpens behind the scan line; the reveal only moves forward, and once complete the picture stays still.
The KEY control (+/-) transposes the scale (default D). The coin is an original pixel Earth: the NASA insignia must not be used.

**STYLE: MELODY (default, `frontend/arcade/vision.js`)**: computer vision composes a song instead of playing raw pixels.
The STYLE button (or V) switches back to the RAW mapping above.
- *Global* (whole picture): brightness + warmth + colourfulness = "valence" → mode, from dark phrygian / aeolian to
  bright ionian / lydian; edge density + contrast = "energy" → tempo (78–132 BPM), bass bounce, drum density.
  The 8 bars follow home → away → tension → home; each bar's brightness picks the chord inside that function.
- *Local* (cells): saliency (centre-surround contrast + unusual colour + Sobel edges, weighted by brightness) → the
  melody follows what the eye is drawn to in each column; a strong edge starts a note (off-beat = syncopation, moving
  in the direction the edge points); the colour of the eye-catching part picks the melody voice; cloud/ice cells play hi-hats.
- *Merge*: the contour is stretched to the melody's range, notes on the beat snap to the bar's chord, leaps are capped at a
  fifth, and the last bar resolves to the key note. `score.why` explains each record in one paragraph (it is also read out).
All knobs are in `COMPOSE`; `?debug` logs the features.

Flow: PRESS ENTER TO START (browsers block sound until a key press or click) -> background ambience + voice
"Welcome to this earthly experience" -> sound tour: each element is named and played with the exact voice the
sonification uses -> Enter/Space scrolls to the coin -> voice "Insert a coin, press enter or space" -> Enter/Space
inserts it (tap on touch-only devices) -> the planetary jukebox: a turntable whose record label is the whole Earth
(EPIC), and a board of records A1..D9. Type a letter + number or click a record; with no choice, a surprise record
plays after 8 s. Each new choice needs another coin. Sound is on by default. Voice clips: `frontend/arcade/voice/*.wav`
(regenerate with `backend/scripts/make_voice.py`, or replace them with your own recordings, same file names).

Calm by design (photosensitivity / vestibular): no flicker, blinking, flashes or rolling scanlines; the picture sits
above the CRT overlay; the record turns slowly (1 turn / 30 s) only while playing, and not at all with "reduce motion".

## Player
```powershell
python backend\scripts\poc2_export_tracks.py       # -> frontend\player\tracks.json
python backend\scripts\poc3_validate_inversion.py  # -> frontend\player\frames\ (needs backend\data\raw)
cd frontend\player; python -m http.server 8000      # open http://localhost:8000
```
Keys: Space, arrows, Shift+arrows, R, D, B, M; aria-live announcements; no autoplay.
`frames/` is generated (~70 MB) and gitignored.
