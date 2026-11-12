// Chiptune engine on plain Web Audio: square / pulse / triangle / noise voices,
// arcade sound effects, and a lookahead player for a sonify() score.
import { VOICES } from "./sonify.js";

const midiHz = m => 440 * Math.pow(2, (m - 69) / 12);

export class Chip {
  constructor() { this.ctx = null; this.on = false; this.level = 0.6; }

  // Must be called from a user gesture (coin, unmute, play): no autoplay.
  ensure() {
    if (!this.ctx) {
      const ctx = this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      this.master = ctx.createGain(); this.master.gain.value = 0;
      const comp = ctx.createDynamicsCompressor();
      comp.threshold.value = -14; comp.ratio.value = 4;
      this.master.connect(comp).connect(ctx.destination);
      this.pulse = { pulse25: this.pulseWave(0.25), pulse12: this.pulseWave(0.125) };
      const len = ctx.sampleRate * 2, buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      this.noiseBuf = buf;
    }
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  }

  setOn(on) {
    this.on = on;
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(t);
    this.master.gain.setTargetAtTime(on ? this.level : 0, t, 0.03);
  }

  get now() { return this.ctx ? this.ctx.currentTime : 0; }

  pulseWave(duty) {
    const n = 64, re = new Float32Array(n), im = new Float32Array(n);
    for (let k = 1; k < n; k++) re[k] = (2 / (k * Math.PI)) * Math.sin(k * Math.PI * duty);
    return this.ctx.createPeriodicWave(re, im);
  }

  // One note. wave: square | pulse25 | pulse12 | triangle | noise.
  note({ midi, t, dur, vel = 0.5, wave = "square", pan = 0, slideTo = null, dest = this.master, soft = false }) {
    const ctx = this.ctx; if (!ctx) return;
    const p = ctx.createStereoPanner(); p.pan.value = pan;
    const g = ctx.createGain();
    const peak = vel * 0.22, end = t + dur;
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(peak, t + (soft ? 0.15 : 0.004));
    if (!soft) g.gain.setTargetAtTime(peak * 0.55, t + 0.01, 0.05);   // quick decay, like an old sound chip
    g.gain.setTargetAtTime(0, end - (soft ? 0.4 : 0.02), soft ? 0.25 : 0.02);
    g.connect(p).connect(dest);
    let src;
    if (wave === "noise") {
      src = ctx.createBufferSource(); src.buffer = this.noiseBuf; src.loop = true;
      const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = midiHz(midi) * 4; bp.Q.value = 6;
      const boost = ctx.createGain(); boost.gain.value = 3;
      src.connect(bp).connect(boost).connect(g);
      src.start(t, Math.random()); src.stop(end + 0.1);
      return;
    }
    src = ctx.createOscillator();
    if (wave.startsWith("pulse")) src.setPeriodicWave(this.pulse[wave]); else src.type = wave;
    src.frequency.setValueAtTime(midiHz(midi), t);
    if (slideTo != null) src.frequency.exponentialRampToValueAtTime(midiHz(slideTo), end);
    src.connect(g); src.start(t); src.stop(end + 0.1);
  }

  // ---- voice-over clips -------------------------------------------------------------------
  async loadSample(url) {
    const bytes = await (await fetch(url)).arrayBuffer();
    return this.ensure().decodeAudioData(bytes);
  }

  speak(buf, gain = 1.1) {              // one clip at a time; a new line cuts the previous one
    if (!this.ctx || !buf) return 0;
    try { this.voice?.stop(); } catch { /* already ended */ }
    const s = this.ctx.createBufferSource(), g = this.ctx.createGain();
    s.buffer = buf; g.gain.value = gain;
    s.connect(g).connect(this.master); s.start(this.now + 0.05);
    this.voice = s;
    this.duck(buf.duration + 0.1);
    return buf.duration;
  }

  stopVoice() { try { this.voice?.stop(); } catch { /* already ended */ } this.voice = null; }

  // ---- background ambience: "you are inside" -------------------------------------------
  // A soft drone (D + A), a slow wind bed, and a gentle generative melody on the pentatonic.
  startAmbient(level = 0.55) {
    if (!this.ctx || this.amb) return;
    const ctx = this.ctx, out = ctx.createGain(), t = this.now;
    out.gain.setValueAtTime(0, t); out.gain.setTargetAtTime(level, t, 1.2);   // slow fade in
    out.connect(this.master);
    const srcs = [];
    [[38, -4], [45, 4]].forEach(([m, det]) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = "triangle"; o.frequency.value = midiHz(m); o.detune.value = det; g.gain.value = 0.06;
      o.connect(g).connect(out); o.start(); srcs.push(o);
    });
    const n = ctx.createBufferSource(), bp = ctx.createBiquadFilter(), ng = ctx.createGain();
    n.buffer = this.noiseBuf; n.loop = true; bp.type = "bandpass"; bp.frequency.value = 500; bp.Q.value = 0.7; ng.gain.value = 0.03;
    const lfo = ctx.createOscillator(), lg = ctx.createGain();              // the wind rises and falls
    lfo.frequency.value = 0.06; lg.gain.value = 320; lfo.connect(lg).connect(bp.frequency);
    n.connect(bp).connect(ng).connect(out); n.start(); lfo.start(); srcs.push(n, lfo);
    const scale = [0, 3, 5, 7, 10];
    let deg = 6, next = t + 1.2;
    const timer = setInterval(() => {
      while (next < this.now + 0.5) {
        deg = Math.max(3, Math.min(12, deg + [-2, -1, -1, 1, 1, 2][Math.floor(Math.random() * 6)]));
        if (Math.random() < 0.65) {
          const midi = 50 + 12 * Math.floor(deg / 5) + scale[deg % 5];
          this.note({ midi, t: next, dur: 1.6, vel: 0.22, wave: "triangle", pan: Math.random() * 0.8 - 0.4, dest: out, soft: true });
        }
        next += 0.8;
      }
    }, 120);
    this.amb = { out, srcs, timer, level };
  }

  stopAmbient(fade = 1.0) {
    const a = this.amb; if (!a) return;
    this.amb = null; clearInterval(a.timer);
    a.out.gain.cancelScheduledValues(this.now);
    a.out.gain.setTargetAtTime(0, this.now, fade / 4);
    a.srcs.forEach(s => { try { s.stop(this.now + fade + 0.2); } catch { /* stopped */ } });
  }

  duck(seconds) {                  // lower the ambience while the voice speaks
    const a = this.amb; if (!a) return;
    const g = a.out.gain, t = this.now;
    g.cancelScheduledValues(t);
    g.setTargetAtTime(a.level * 0.35, t, 0.08);
    g.setTargetAtTime(a.level, t + seconds, 0.4);
  }

  // ---- element demos: the exact voices the sonification uses ------------------------------
  demo(voiceKey) {
    const v = VOICES[voiceKey], t0 = this.now + 0.05;
    const phrases = {   // [midi, start beat, length beats], beat = 0.2 s
      triangle: [[62, 0, 2], [65, 1.5, 2], [67, 3, 2], [69, 4.5, 3], [67, 7, 2], [65, 8.5, 2], [62, 10, 4]],          // water: slow, rolling
      pulse:    [[50, 0, 1], [57, 1, 1], [55, 2, 1], [57, 3, 1], [53, 4, 1], [57, 5, 1], [50, 6, 1], [57, 7, 2], [62, 9, 3]], // land: steady steps
      square:   [[74, 0, .5], [77, .6, .5], [74, 1.1, .4], [81, 1.6, .6], [79, 2.4, .4], [84, 2.9, .5], [81, 3.5, .4], [86, 4, .5], [84, 4.7, .4], [81, 5.2, .6], [79, 6, .5], [77, 6.6, .5], [81, 7.2, 1], [74, 8.4, 2]], // fire: fast crackle
      noise:    [[72, 0, 3], [77, 2.5, 3], [81, 5, 4], [79, 8, 3], [74, 10, 5]],                                         // wind: gusts
    }[voiceKey];
    const beat = 0.2;
    let end = 0;
    phrases.forEach(([m, b, l], i) => {
      const t = t0 + b * beat, dur = l * beat;
      this.note({ midi: m, t, dur, vel: 0.75 * v.gain, wave: v.wave, pan: -0.5 + i / phrases.length });
      end = Math.max(end, b * beat + dur);
    });
    this.duck(end);
    return end;
  }

  // ---- sound effects (original designs) -------------------------------------------------
  blip(midi = 84) { if (!this.ctx) return; this.note({ midi, t: this.now + 0.01, dur: 0.05, vel: 0.35, wave: "pulse25" }); }

  coin() {
    const t = this.now + 0.02;
    // two bright clinks falling in pitch, a short rattle down the chute, then a soft thunk
    this.note({ midi: 91, t, dur: 0.07, vel: 0.6, wave: "square" });
    this.note({ midi: 86, t: t + 0.08, dur: 0.18, vel: 0.55, wave: "square" });
    for (let i = 0; i < 5; i++) this.note({ midi: 100 - i * 2, t: t + 0.28 + i * 0.045 * (1 + i * 0.25), dur: 0.025, vel: 0.35, wave: "noise" });
    this.note({ midi: 45, t: t + 0.62, dur: 0.18, vel: 0.9, wave: "triangle", slideTo: 28 });
    this.note({ midi: 40, t: t + 0.62, dur: 0.08, vel: 0.5, wave: "noise" });
    return 0.85;
  }

  jingle() {          // "track loaded": a rising D minor arpeggio
    const t = this.now + 0.05, seq = [62, 65, 69, 74, 77, 81];
    seq.forEach((m, i) => this.note({ midi: m, t: t + i * 0.07, dur: i === seq.length - 1 ? 0.35 : 0.08, vel: 0.45, wave: "pulse25" }));
    this.note({ midi: 38, t, dur: 0.5, vel: 0.6, wave: "triangle" });
    return 0.8;
  }

  over() {            // "track complete": falling resolution to D
    const t = this.now + 0.05;
    [81, 77, 74, 69, 62].forEach((m, i) => this.note({ midi: m, t: t + i * 0.1, dur: 0.12, vel: 0.4, wave: "pulse25" }));
    this.note({ midi: 50, t: t + 0.5, dur: 0.6, vel: 0.5, wave: "triangle" });
  }

  playColumn(col, t = this.now + 0.02) {
    col.notes.forEach(n => {
      const v = VOICES[n.voice];
      // len = how many columns the note is held (melody mode); wave / slideTo override the voice (drums)
      this.note({ midi: n.midi, t, dur: col.dur * (n.len ?? 1) * 0.92, vel: n.vel * v.gain, wave: n.wave ?? v.wave, pan: n.pan, slideTo: n.slideTo ?? null });
    });
  }
}

// Lookahead scheduler (same pattern as frontend/player/index.html): audio is scheduled ahead on the
// audio clock; the UI follows the audio clock on requestAnimationFrame.
export class Player {
  constructor(chip, { onColumn, onEnd } = {}) {
    this.chip = chip; this.onColumn = onColumn; this.onEnd = onEnd;
    this.score = null; this.playing = false; this.next = 0; this.queue = []; this.pos = 0;
  }

  load(score) { this.stop(); this.score = score; this.pos = 0; }

  // swap in a re-scored track (e.g. new key) without losing the playhead
  setScore(score) {
    const was = this.playing, pos = this.pos;
    this.stop(); this.score = score; this.pos = pos;
    if (was) this.play(pos);
  }

  play(from = this.pos) {
    if (!this.score) return;
    this.chip.ensure();
    if (from >= this.score.columns.length) from = 0;
    this.playing = true; this.next = from; this.pos = from; this.queue = [];
    this.nextTime = this.chip.now + 0.08;
    this.timer = setInterval(() => this.tick(), 25);
    this.tick();
    const frame = () => { if (!this.playing) return; this.drain(); this.raf = requestAnimationFrame(frame); };
    this.raf = requestAnimationFrame(frame);
  }

  tick() {
    const cols = this.score.columns;
    while (this.playing && this.next < cols.length && this.nextTime < this.chip.now + 0.2) {
      const c = cols[this.next];
      this.chip.playColumn(c, this.nextTime);
      this.queue.push({ i: this.next, t: this.nextTime });
      this.nextTime += c.dur; this.next++;
    }
    if (this.next >= cols.length && !this.endAt) this.endAt = this.nextTime;
  }

  drain() {
    const now = this.chip.now;
    while (this.queue.length && this.queue[0].t <= now) {
      const { i, t } = this.queue.shift();
      this.pos = i;
      this.onColumn?.(i, Math.min(1, (now - t) / this.score.columns[i].dur));
    }
    if (this.queue.length === 0 && this.endAt && now >= this.endAt) {
      this.stop(); this.pos = this.score.columns.length; this.onEnd?.();
    } else if (this.playing) {
      const c = this.score.columns[this.pos], start = this.queue.length ? this.queue[0].t - c.dur : this.endAt - c.dur;
      this.onColumn?.(this.pos, Math.max(0, Math.min(1, (now - start) / c.dur)));
    }
  }

  stop() {
    this.playing = false; this.endAt = 0; this.queue = [];
    clearInterval(this.timer); cancelAnimationFrame(this.raf);
  }

  pause() { const resumeAt = this.pos; this.stop(); this.pos = resumeAt; }

  step(n) {
    if (!this.score) return;
    this.pause();
    this.pos = Math.max(0, Math.min(this.score.columns.length - 1, this.pos + n));
    this.chip.ensure(); this.chip.playColumn(this.score.columns[this.pos]);
    this.onColumn?.(this.pos, 1);
  }
}
