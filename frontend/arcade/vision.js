// Computer vision -> composition. Pure functions, no audio, same score shape as sonify().
//
//   GLOBAL  (the whole picture)  -> the mood: mode, tempo, chord progression, how busy the band is
//   LOCAL   (each cell / column) -> the melody (saliency), its rhythm (edges), the drums (clouds, edges)
//   MERGE                        -> the melody is snapped onto the chord of its bar, leaps are limited,
//                                   and the song starts and ends at home (the tonic), so it sounds composed.
//
// Every knob is in COMPOSE; every decision is explained in score.why and per column in column.chord.
import { rgbToHsv, voiceFor, noteName, MAPPING } from "./sonify.js";

export const COMPOSE = {
  stepsPerBar: 8,          // 64 columns = 8 bars of eighth notes
  bpm: [78, 132],          // calm, smooth picture .. busy, high-contrast picture
  melodyOffset: 12,        // melody starts one octave above the key's tonic (D4 by default)
  melodyDegrees: 12,       // melody range in scale steps (about 1.7 octaves)
  maxLeap: 4,              // largest melodic jump, in scale steps (a fifth)
  restBelow: 0.1,          // a column darker than this (relative) makes the melody rest
  onsetEdge: 0.4,          // an edge at least this strong under the melody starts a new note
  smooth: 0.45,            // how much the melody contour remembers the previous column (0..1)
};

// Darkest -> brightest. The picture's "valence" picks one.
export const MODES = [
  { name: "phrygian",   steps: [0, 1, 3, 5, 7, 8, 10] },
  { name: "aeolian",    steps: [0, 2, 3, 5, 7, 8, 10] },
  { name: "dorian",     steps: [0, 2, 3, 5, 7, 9, 10] },
  { name: "mixolydian", steps: [0, 2, 4, 5, 7, 9, 10] },
  { name: "ionian",     steps: [0, 2, 4, 5, 7, 9, 11] },
  { name: "lydian",     steps: [0, 2, 4, 6, 7, 9, 11] },
];

// Harmonic functions -> scale degrees (0 = I). The picture chooses inside each group.
const GROUPS = { T: [0, 5, 2], S: [3, 1, 5], D: [4, 6, 1] };
const FORM = ["T", "S", "D", "T"];       // home, away, tension, home: repeated, with a cadence at the end
const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"];
const SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const FLAT_STEPS = new Set([1, 3, 8, 10]);             // lowered 2nd, 3rd, 6th, 7th are spelled with flats

const clamp01 = v => Math.max(0, Math.min(1, v));
const lerp = (a, b, t) => a + (b - a) * t;
const avg = a => { let s = 0; for (const v of a) s += v; return s / a.length; };
const sd = a => { const m = avg(a); let s = 0; for (const v of a) s += (v - m) ** 2; return Math.sqrt(s / a.length); };
const pct = (a, p) => { const s = Float32Array.from(a).sort(); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
const normBy = (a, p = 0.98) => { const h = Math.max(1e-6, pct(a, p)); return a.map(v => Math.min(1, v / h)); };

// ------------------------------------------------------------------------------------------------
// Vision: features of the picture. imageData = the cols x rows grid (one pixel per cell).
export function analyse(imageData, M = MAPPING) {
  const { width: W, height: H, data } = imageData, N = W * H;
  const L = new Float32Array(N), RG = new Float32Array(N), YB = new Float32Array(N), cells = [];
  let warm = 0;
  for (let i = 0; i < N; i++) {
    const r = data[i * 4] / 255, g = data[i * 4 + 1] / 255, b = data[i * 4 + 2] / 255;
    L[i] = 0.2126 * r + 0.7152 * g + 0.0722 * b;          // luminance
    RG[i] = r - g; YB[i] = 0.5 * (r + g) - b;              // opponent colours (Hasler & Süsstrunk)
    warm += r - b;
    const hsv = rgbToHsv(data[i * 4], data[i * 4 + 1], data[i * 4 + 2]);
    cells.push({ ...hsv, voice: voiceFor(hsv, M) });
  }
  const at = (A, x, y) => A[Math.max(0, Math.min(H - 1, y)) * W + Math.max(0, Math.min(W - 1, x))];

  // brightness relative to this picture (as in sonify), so night scenes still use the full range
  const lo = pct(L, 0.05), hi = Math.max(lo + 1e-3, pct(L, 0.98));
  const vn = L.map(v => clamp01((v - lo) / (hi - lo)));

  // Sobel edges, centre-surround contrast (5x5 surround), local texture (3x3 std)
  const edgeRaw = new Float32Array(N), up = new Int8Array(N), cs = new Float32Array(N), tex = new Float32Array(N), cd = new Float32Array(N);
  const mRG = avg(RG), mYB = avg(YB);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    const gx = at(L, x + 1, y - 1) + 2 * at(L, x + 1, y) + at(L, x + 1, y + 1) - at(L, x - 1, y - 1) - 2 * at(L, x - 1, y) - at(L, x - 1, y + 1);
    const gy = at(L, x - 1, y + 1) + 2 * at(L, x, y + 1) + at(L, x + 1, y + 1) - at(L, x - 1, y - 1) - 2 * at(L, x, y - 1) - at(L, x + 1, y - 1);
    edgeRaw[i] = Math.hypot(gx, gy);
    up[i] = gy < -1e-3 ? 1 : gy > 1e-3 ? -1 : 0;           // edge direction: +1 = brighter above
    let s = 0, n = 0, s1 = 0, s2 = 0;
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      const v = at(L, x + dx, y + dy); s += v; n++;
      if (Math.abs(dx) <= 1 && Math.abs(dy) <= 1) { s1 += v; s2 += v * v; }
    }
    cs[i] = Math.abs(L[i] - s / n);
    tex[i] = Math.sqrt(Math.max(0, s2 / 9 - (s1 / 9) ** 2));
    cd[i] = Math.hypot(RG[i] - mRG, YB[i] - mYB);          // how unusual this colour is for the picture
  }
  const edge = normBy(edgeRaw), csn = normBy(cs), cdn = normBy(cd);
  // Saliency: what the eye is drawn to. Contrast with the surroundings + unusual colour + edges,
  // weighted by brightness so the black of space never steals the melody.
  let sal = new Float32Array(N);
  for (let i = 0; i < N; i++) sal[i] = (0.45 * csn[i] + 0.35 * cdn[i] + 0.2 * edge[i]) * (0.25 + 0.75 * vn[i]);
  sal = normBy(sal, 1);

  // Global features
  const meanL = avg(L), contrast = sd(L), warmth = warm / N;
  const colourful = clamp01((Math.hypot(sd(RG), sd(YB)) + 0.3 * Math.hypot(mRG, mYB)) / 0.35);
  const edgeDensity = clamp01((avg(edgeRaw) - 0.1) / 0.6);
  const share = { triangle: 0, pulse: 0, square: 0, noise: 0 };
  let tw = 0;
  cells.forEach((c, i) => { share[c.voice] += vn[i]; tw += vn[i]; });
  for (const k in share) share[k] = tw ? share[k] / tw : 0;
  const valence = clamp01(0.45 * clamp01(meanL / 0.55) + 0.35 * clamp01(0.5 + warmth * 2.5) + 0.2 * colourful);
  const energy = clamp01(0.6 * edgeDensity + 0.4 * clamp01(contrast / 0.28));

  return { W, H, cells, vn, edge, up, sal, tex,
    global: { meanL, contrast, warmth, colourful, edgeDensity, valence, energy, share } };
}

// ------------------------------------------------------------------------------------------------
// Composition: global mood + local melody, merged.
export function compose(imageData, M = MAPPING, C = COMPOSE) {
  const A = analyse(imageData, M), { W: cols, H: rows, vn, sal, edge, up, cells } = A, G = A.global;
  const mode = MODES[Math.round(G.valence * (MODES.length - 1))], S = mode.steps;
  const tonic = M.tonicMidi, bpm = Math.round(lerp(C.bpm[0], C.bpm[1], G.energy)), stepDur = 60 / bpm / 2;
  const spb = C.stepsPerBar, bars = Math.max(1, Math.ceil(cols / spb));
  const barOf = x => Math.min(bars - 1, Math.floor(x / spb));
  const deg2midi = (d, base) => base + 12 * Math.floor(d / 7) + S[((d % 7) + 7) % 7];
  const quality = d => {
    const r = S[d], t = (S[(d + 2) % 7] - r + 12) % 12, f = (S[(d + 4) % 7] - r + 12) % 12;
    return f === 6 ? "dim" : t === 4 ? "maj" : "min";
  };
  const chordLabel = d => {
    const q = quality(d), root = (FLAT_STEPS.has(S[d]) ? FLATS : SHARPS)[(tonic + S[d]) % 12];   // Bb, not A#, for a flat 7th
    const rn = q === "maj" ? ROMAN[d] : ROMAN[d].toLowerCase() + (q === "dim" ? "°" : "");
    return `${root}${q === "min" ? "m" : q === "dim" ? "dim" : ""} (${rn})`;
  };
  const cell = (x, y) => y * cols + x;

  // per-column local summaries
  const colMean = [], colEdge = [], colWind = [];
  for (let x = 0; x < cols; x++) {
    let v = 0, e = 0, w = 0;
    for (let y = 0; y < rows; y++) { const i = cell(x, y); v += vn[i]; e += edge[i]; if (cells[i].voice === "noise") w += vn[i]; }
    colMean.push(v / rows); colEdge.push(e / rows); colWind.push(v ? w / v : 0);
  }

  // 1) GLOBAL -> harmony. The form gives the musical shape; each bar's brightness picks the chord.
  const barV = [...Array(bars)].map((_, b) => avg(colMean.slice(b * spb, (b + 1) * spb)));
  const gV = avg(barV);
  const chords = [];
  for (let b = 0; b < bars; b++) {
    const fn = b === bars - 1 ? "T" : b === bars - 2 ? "D" : FORM[b % FORM.length];
    if (b === 0 || b === bars - 1) { chords.push(0); continue; }
    let opts = GROUPS[fn].filter(d => quality(d) !== "dim" && d !== chords[b - 1]);
    if (!opts.length) opts = [{ T: 0, S: 3, D: 4 }[fn]];
    const f = clamp01(0.5 + (barV[b] - gV) * 2.5);          // brighter than average -> later option
    chords.push(opts[Math.min(opts.length - 1, Math.floor(f * opts.length))]);
  }
  const chordTones = d => [d, d + 2, d + 4].map(t => ((t % 7) + 7) % 7);
  const snapToChord = (deg, d) => {                         // nearest chord tone inside the range
    const pcs = chordTones(d);
    let best = deg, bd = 99;
    for (let c = 0; c < C.melodyDegrees; c++) {
      if (!pcs.includes(c % 7)) continue;
      const dist = Math.abs(c - deg);
      if (dist < bd || (dist === bd && c < best)) { bd = dist; best = c; }
    }
    return best;
  };

  // melody voice per bar: the element (colour) of the cells the eye is drawn to; WIND goes to drums
  const barVoice = [...Array(bars)].map((_, b) => {
    const w = { triangle: 0, pulse: 0, square: 0 };
    for (let x = b * spb; x < Math.min(cols, (b + 1) * spb); x++)
      for (let y = 0; y < rows; y++) { const i = cell(x, y); if (cells[i].voice !== "noise") w[cells[i].voice] += sal[i] * vn[i]; }
    const top = Object.entries(w).sort((p, q) => q[1] - p[1])[0];
    return top[1] > 0 ? top[0] : "triangle";
  });

  // 2) LOCAL -> melody. Contour = saliency centroid of each column; edges decide where notes start.
  const contour = [], confs = [];
  let sm = null;
  for (let x = 0; x < cols; x++) {
    let sw = 0, sy = 0, conf = 0;
    for (let y = 0; y < rows; y++) { const s = sal[cell(x, y)], w = s * s; sw += w; sy += w * y; conf = Math.max(conf, s); }
    const cy = sw > 1e-9 ? sy / sw : (rows - 1) / 2;
    sm = sm == null ? cy : C.smooth * sm + (1 - C.smooth) * cy;
    contour.push(sm); confs.push(conf);
  }
  // MERGE (global x local): stretch this picture's contour to the full melody range, so a picture
  // whose eye-catching parts sit in a narrow band still gets a melody that rises and falls.
  const cLo = pct(contour, 0.05), cHi = Math.max(cLo + 1, pct(contour, 0.95));
  const mel = [];                                            // per column: {deg,row,onset,vel} | null (rest)
  let prev = null;
  const lastBar = (bars - 1) * spb;
  for (let x = 0; x < cols; x++) {
    const sm = contour[x], conf = confs[x];
    const row = Math.round(sm), step = x % spb, b = barOf(x);
    if (x > lastBar && prev) { mel.push({ ...prev, onset: false }); continue; }   // final note rings out
    if (colMean[x] < C.restBelow && x !== lastBar) { mel.push(null); prev = null; continue; }

    let deg = Math.round(clamp01((cHi - sm) / (cHi - cLo)) * (C.melodyDegrees - 1));   // higher in the picture = higher
    if (prev) deg = Math.max(prev.deg - C.maxLeap, Math.min(prev.deg + C.maxLeap, deg));   // 3) MERGE: no wild leaps
    const onBeat = step % 2 === 0;
    if (onBeat) deg = snapToChord(deg, chords[b]);                                        // MERGE: fit the chord
    if (x === lastBar) deg = deg >= 4 ? 7 : 0;                                            // MERGE: end at home
    const vel = +(0.45 + 0.45 * conf).toFixed(3);
    const ci = cell(x, Math.min(rows - 1, Math.max(0, row))), e = edge[ci];
    let onset;
    if (!prev || step === 0 || step === 4 || x === lastBar) onset = true;   // every half bar
    else if (deg !== prev.deg) onset = onBeat || e >= C.onsetEdge;          // new note on the beat, or on an edge (syncopation)
    else if (onBeat) onset = e >= C.onsetEdge * 0.5;                        // same note: re-strike on a softer edge
    else if (e >= C.onsetEdge && up[ci]) { deg = Math.max(0, Math.min(C.melodyDegrees - 1, deg + up[ci])); onset = true; }
    else onset = false;                                                     // off the beat, a sharp edge adds a passing note
                                                                            // in the direction the edge points
    if (!onset) { mel.push({ ...prev, onset: false }); continue; }
    prev = { deg, row, vel, onset: true };
    mel.push(prev);
  }

  // build columns
  const columns = [];
  let duration = 0;
  for (let x = 0; x < cols; x++) {
    const b = barOf(x), step = x % spb, d = chords[b], notes = [];
    const pan = cols > 1 ? +(-0.8 + 1.6 * x / (cols - 1)).toFixed(3) : 0;
    const m = mel[x];
    if (m && m.onset) {
      let len = 1;
      while (x + len < cols && mel[x + len] && !mel[x + len].onset) len++;
      notes.push({ part: "melody", row: m.row, midi: deg2midi(m.deg, tonic + C.melodyOffset), vel: m.vel, voice: barVoice[b], pan, len });
    }
    // bass: chord root, bouncing octaves when the picture is busy
    const busy = G.energy > 0.55;
    const bassPat = busy ? { 0: d, 2: d + 7, 4: d + 4, 6: d + 7 } : { 0: d, 4: d + 4 };
    if (bassPat[step] != null && !(x > lastBar))
      notes.push({ part: "bass", row: null, midi: deg2midi(bassPat[step], tonic - 12), vel: 0.6, voice: "triangle", pan: 0, len: busy ? 2 : 4 });
    if (x === lastBar) notes.push({ part: "bass", row: null, midi: deg2midi(0, tonic - 12), vel: 0.6, voice: "triangle", pan: 0, len: cols - x });
    // harmony: the chord as an arpeggio; colourful pictures arpeggiate twice as fast
    const arpVoice = barVoice[b] === "triangle" ? "pulse" : barVoice[b], tones = [d, d + 2, d + 4, d + 2];
    if (x === lastBar) chordTones(0).forEach(t => notes.push({ part: "harmony", row: null, midi: deg2midi(t, tonic), vel: 0.18, voice: "pulse", wave: "pulse12", pan: -pan * 0.6, len: cols - x }));
    else if (x < lastBar && (G.colourful > 0.45 || step % 2 === 0))
      notes.push({ part: "harmony", row: null, midi: deg2midi(tones[(G.colourful > 0.45 ? step : step / 2) % 4], tonic), vel: 0.18, voice: arpVoice, wave: "pulse12", pan: +(-pan * 0.6).toFixed(3), len: G.colourful > 0.45 ? 1 : 2 });
    // drums (from bar 2, so the picture gets a short intro): local clouds = hi-hat, local edges = snare
    if (b >= 1 && x < lastBar) {
      if (step === 0 || (step === 4 && G.energy > 0.3))
        notes.push({ part: "drums", row: null, midi: 45, slideTo: 28, vel: 0.75, voice: "triangle", pan: 0, len: 0.6 });
      if ((step === 2 || step === 6) && (colEdge[x] > 0.35 || G.energy > 0.6))
        notes.push({ part: "drums", row: null, midi: 64, vel: 0.35, voice: "noise", pan: 0, len: 0.35 });
      if ((step % 2 === 1 || G.energy > 0.7) && colWind[x] > 0.15)
        notes.push({ part: "drums", row: null, midi: 98, vel: +(0.12 + 0.4 * colWind[x]).toFixed(3), voice: "noise", pan: +(pan * 0.5).toFixed(3), len: 0.3 });
    }
    notes.sort((p, q) => p.midi - q.midi);
    columns.push({ x, start: duration, dur: stepDur, mean: colMean[x], notes, chord: chordLabel(d), bar: b + 1 });
    duration += stepDur;
  }

  const key = noteName(tonic).replace(/-?\d+$/, "");
  const why =
    `${G.meanL > 0.35 ? "Bright" : "Dark"}, ${G.warmth > 0.03 ? "warm" : "cool"}${G.colourful > 0.45 ? ", colourful" : ""} picture, so ${key} ${mode.name}. ` +
    `${G.edgeDensity > 0.5 ? "Lots of edges and detail" : "Smooth, calm shapes"}, so ${bpm} beats per minute. ` +
    `The melody follows what the eye is drawn to in each column, edges start new notes, and it is fitted to the chords: ` +
    `${chords.map(chordLabel).map(c => c.split(" ")[0]).join(", ")}. ` +
    `${G.share.noise > 0.15 ? "Clouds and ice play the hi-hats." : "Few clouds, so the hi-hats stay quiet."}`;

  return { kind: "melody", cols, rows, cells, columns, duration, bpm, mode: mode.name, key, chords: chords.map(chordLabel), features: G, why };
}

export const COMPOSE_TEXT =
  "Computer vision listens to the whole picture first: brightness, warmth and colour choose the mode, from dark " +
  "phrygian to bright lydian, and the amount of edges and contrast sets the tempo. Then it looks closely: in each " +
  "column the melody follows what the eye is drawn to (contrast, unusual colour, edges), higher in the picture is " +
  "higher, and sharp edges start new notes. Both are merged: the melody lands on the chord of each bar, never jumps " +
  "too far, and comes home to the key note at the end. Clouds and ice play the hi-hats; the colour of the eye-catching " +
  "part picks the melody instrument.";
