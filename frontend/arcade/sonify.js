// Image -> score. Pure functions, no audio, so the mapping can be tested and explained.
// Every note comes from one grid cell of the picture: tune everything in MAPPING.

export const MAPPING = {
  cols: 64,                 // time steps (scan left -> right)
  pitchSteps: 15,           // scale steps from bottom row to top row (D3 .. C6)
  scale: [0, 3, 5, 7, 10],  // D minor pentatonic, same as backend/jukebox/mapping.py
  tonicMidi: 50,            // D3 = bottom of the image
  stepSec: 0.2,             // base length of one column
  tempo: [0.8, 1.3],        // speed multiplier: dark column .. bright column
  minBright: 0.22,          // normalised brightness below this is silent
  maxVoices: 4,             // loudest cells per column
  greySat: 0.16,            // below this saturation a cell is "grey" (cloud, ice, smoke)
};

// Hue families -> chiptune voices. Order = legend order.
export const VOICES = {
  triangle: { label: "WATER", wave: "triangle", color: "#3ec7ff", gain: 1.0, what: "blue (ocean, lakes, sky)" },
  pulse:    { label: "LAND",  wave: "pulse25",  color: "#5dff7a", gain: 0.55, what: "green and brown (forest, soil, aurora)" },
  square:   { label: "FIRE",  wave: "square",   color: "#ff5a3c", gain: 0.45, what: "red, orange, yellow (fire, desert, heat)" },
  noise:    { label: "WIND",  wave: "noise",    color: "#f4f1ea", gain: 0.7, what: "white and grey (clouds, wind, ice, smoke)" },
};

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
export const noteName = m => NOTE_NAMES[((m % 12) + 12) % 12] + (Math.floor(m / 12) - 1);

export function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  let h = 0;
  if (d) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60; if (h < 0) h += 360;
  }
  return { h, s: max ? d / max : 0, v: max };
}

export function voiceFor({ h, s, v }, M = MAPPING) {
  if (s < M.greySat) return "noise";
  if (h >= 170 && h < 265) return "triangle";
  if (h >= 70 && h < 170) return "pulse";
  if (h < 70 || h >= 330) return v < 0.5 ? "pulse" : "square"; // dark orange = brown soil
  return "square";                                               // magenta / purple
}

export function rowToMidi(row, rows, M = MAPPING) {
  const deg = rows > 1 ? Math.round((rows - 1 - row) / (rows - 1) * (M.pitchSteps - 1)) : 0;
  const n = M.scale.length;
  return M.tonicMidi + 12 * Math.floor(deg / n) + M.scale[deg % n];
}

export function gridSize(width, height, M = MAPPING) {
  const cols = M.cols;
  const rows = Math.max(4, Math.min(64, Math.round(cols * height / width)));
  return { cols, rows };
}

function percentile(sorted, p) { return sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))]; }

/**
 * imageData: ImageData of the picture already downsampled to cols x rows (one pixel per cell).
 * Returns { cols, rows, cells, columns: [{ dur, mean, notes: [{row, midi, vel, voice, pan}] }], duration }.
 */
export function sonify(imageData, M = MAPPING) {
  const { width: cols, height: rows, data } = imageData;
  const cells = [];
  for (let i = 0; i < cols * rows; i++) {
    const hsv = rgbToHsv(data[i * 4], data[i * 4 + 1], data[i * 4 + 2]);
    cells.push({ ...hsv, voice: voiceFor(hsv, M) });
  }
  // Brightness relative to this picture (5th..98th percentile), so night scenes and
  // bright cloud decks both use the full dynamic range.
  const vs = cells.map(c => c.v).sort((a, b) => a - b);
  const lo = percentile(vs, 0.05), hi = Math.max(lo + 1e-3, percentile(vs, 0.98));
  cells.forEach(c => { c.vn = Math.min(1, Math.max(0, (c.v - lo) / (hi - lo))); });

  const columns = [];
  let duration = 0;
  for (let x = 0; x < cols; x++) {
    const col = [];
    for (let y = 0; y < rows; y++) col.push({ row: y, ...cells[y * cols + x] });
    const mean = col.reduce((a, c) => a + c.vn, 0) / rows;
    const pan = cols > 1 ? -1 + 2 * x / (cols - 1) : 0;
    const used = new Set();
    const notes = [];
    for (const c of col.filter(c => c.vn >= M.minBright).sort((a, b) => b.vn - a.vn)) {
      const midi = rowToMidi(c.row, rows, M);
      if (used.has(midi)) continue;           // several rows can share one scale step
      used.add(midi);
      notes.push({ row: c.row, midi, vel: +(0.25 + 0.75 * c.vn).toFixed(3), voice: c.voice, pan: +pan.toFixed(3) });
      if (notes.length >= M.maxVoices) break;
    }
    notes.sort((a, b) => a.midi - b.midi);
    const speed = M.tempo[0] + (M.tempo[1] - M.tempo[0]) * mean;
    const dur = M.stepSec / speed;
    columns.push({ x, start: duration, dur, mean, notes });
    duration += dur;
  }
  return { cols, rows, cells, columns, duration };
}

// The melody note of a column: in melody mode the "melody" part, otherwise the highest note.
export const leadNote = column => column.notes.find(n => n.part === "melody") ||
  (column.notes.some(n => n.part) ? null : column.notes[column.notes.length - 1]) || null;

export function dominantVoice(column) {
  const lead = column.notes.filter(n => !n.part || n.part === "melody");
  if (!lead.length) return null;
  const w = {};
  lead.forEach(n => { w[n.voice] = (w[n.voice] || 0) + n.vel; });
  return Object.entries(w).sort((a, b) => b[1] - a[1])[0][0];
}

export function describeColumn(column, cols) {
  const head = `Column ${column.x + 1} of ${cols}`;
  if (column.chord) {                                   // melody mode
    const m = leadNote(column), harm = `bar ${column.bar}, chord ${column.chord.split(" ")[0]}`;
    if (!m) return `${head}, ${harm}: the melody holds or rests here.`;
    return `${head}, ${harm}: melody ${noteName(m.midi)} on ${VOICES[m.voice].label.toLowerCase()}${m.len > 1 ? `, held for ${m.len} steps` : ""}.`;
  }
  if (!column.notes.length) return `${head}: silence, this part of the picture is dark.`;
  const v = VOICES[dominantVoice(column)];
  const top = column.notes[column.notes.length - 1];
  return `${head}: ${column.notes.length} notes, mostly ${v.label.toLowerCase()} (${v.what.split(" (")[0]}), highest ${noteName(top.midi)}.`;
}

export const MAPPING_TEXT =
  "The picture is played from left to right, one column of pixels at a time. Higher in the picture means " +
  "higher notes, on a D minor pentatonic scale. Brighter pixels are louder; dark pixels are silent. " +
  "Colour picks the instrument: blue is water (triangle wave), green and brown are land (pulse wave), " +
  "red, orange and yellow are fire (square wave), white and grey are wind and cloud (noise). " +
  "Bright columns play faster, and the sound moves from your left ear to your right as the scan crosses the picture.";
