import { sonify, gridSize, MAPPING, VOICES, noteName, dominantVoice, describeColumn, leadNote } from "./sonify.js";
import { compose } from "./vision.js";
import { Chip, Player } from "./chip.js";
import { Turntable } from "./turntable.js";

const $ = id => document.getElementById(id);
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const touchOnly = matchMedia("(pointer: coarse)").matches && !matchMedia("(pointer: fine)").matches;
const params = new URLSearchParams(location.search);
const DEBUG = params.has("debug");
const store = {
  get(k) { try { return localStorage.getItem("ej:" + k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem("ej:" + k, v); } catch { /* private mode */ } },
};

const chip = new Chip();
const voice = {};                 // decoded voice-over clips
let manifest = [], current = null, track = null, credits = 0, busy = false, started = false;

// ---------------------------------------------------------------- key (root note)
const KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
let keyIdx = KEY_NAMES.indexOf(store.get("key"));
if (keyIdx < 0) keyIdx = 2;                                   // D, as in backend/jukebox/mapping.py
const applyKey = () => { MAPPING.tonicMidi = 48 + keyIdx; $("keyName").textContent = KEY_NAMES[keyIdx]; };
applyKey();

// ---------------------------------------------------------------- style: MELODY (computer vision composes) | RAW (pixel by pixel)
let style = store.get("style") === "raw" ? "raw" : "melody";
const RULES = {
  melody: "WHOLE PICTURE = MOOD, TEMPO, CHORDS<br>EYE-CATCHING PART = MELODY<br>EDGES START NOTES · CLOUDS = HI-HATS<br>MELODY FITS THE CHORDS, ENDS AT HOME",
  raw: "UP = HIGHER NOTE<br>BRIGHT = LOUD · DARK = SILENT<br>BRIGHT COLUMNS PLAY FASTER<br>SOUND PANS LEFT TO RIGHT",
};
function showStyle() {
  $("styleBtn").textContent = style === "melody" ? "MELODY" : "RAW";
  $("styleBtn").setAttribute("aria-pressed", String(style === "melody"));
  $("styleHelp").textContent = style === "melody" ? "COMPUTER VISION COMPOSES A SONG" : "EVERY PIXEL PLAYS ITSELF";
  $("rules").innerHTML = RULES[style];
  const s = track?.score;
  $("modeName").textContent = s?.mode ? `${s.mode.toUpperCase()} · ${s.bpm} BPM` : style === "melody" ? "MODE FROM THE PICTURE" : "MINOR PENTATONIC";
}
const modeWords = s => s.mode ? `${s.mode}, ${s.bpm} beats per minute` : "minor pentatonic";

// ---------------------------------------------------------------- pixel art
const COIN = [               // original pixel-art Earth coin (no agency marks)
  ".....OYYYYO.....", "...OYYYYYYYYO...", "..OYYBBBBBBYYO..", ".OYYBBGGBBBBYYO.",
  ".OYBBGGGGBBBBYO.", "OYYBGGGGBBBGBYYO", "OYBBBGGBBBGGGBYO", "OYBBBBGBBBGGGBYO",
  "OYBBBBBBBGGGBBYO", "OYBWBBBBBBGBBBYO", "OYYBWBBBBBBBBYYO", ".OYBBBBBGGBBBYO.",
  ".OYYBBBBBBBBYYO.", "..OYYBBBBBBYYO..", "...OYYYYYYYYO...", ".....OOOOOO.....",
];
const PAL = { Y: "#ffd23f", O: "#b8740a", B: "#2f7dd8", G: "#4fcf5a", W: "#f4f1ea" };

function drawCoin() {
  const g = $("coinArt").getContext("2d");
  COIN.forEach((row, y) => [...row].forEach((ch, x) => { if (PAL[ch]) { g.fillStyle = PAL[ch]; g.fillRect(x, y, 1, 1); } }));
}

function drawSlot() {
  const g = $("slot").getContext("2d");
  for (let y = 0; y < 24; y++) for (let x = 0; x < 24; x++) {
    const d = Math.hypot(x + 0.5 - 12, y + 0.5 - 12);
    if (Math.abs(d - 10.5) < 0.75) { g.fillStyle = "#f4f1ea"; g.fillRect(x, y, 1, 1); }
  }
  g.fillStyle = "#000"; g.fillRect(11, 6, 2, 12);                 // the slit
  g.fillStyle = "#ffb000"; g.fillRect(10, 6, 1, 12); g.fillRect(13, 6, 1, 12);
}

// ---------------------------------------------------------------- helpers
function say(text) { $("live").textContent = ""; requestAnimationFrame(() => { $("live").textContent = text; }); }
function setCredit(n) { credits = n; $("credit").textContent = "CREDIT " + String(n).padStart(2, "0"); }
function setSound(on) {                       // sound is on by default; MUTE only lasts this visit
  if (on) chip.ensure();
  chip.setOn(on);
  $("mute").textContent = on ? "MUTE" : "UNMUTE";
  $("mute").setAttribute("aria-pressed", String(on));
}
chip.on = true;

function randomIndex() {               // surprise record: never the same as last time
  const last = store.get("last");
  const pool = manifest.map((m, i) => i).filter(i => manifest.length < 2 || (manifest[i].id !== last && manifest[i] !== current));
  return pool[Math.floor(Math.random() * pool.length)];
}

function loadImage(src) {
  return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = src; });
}

const visible = el => { const r = el.getBoundingClientRect(); return !el.hidden && r.top < innerHeight * 0.5 && r.bottom > innerHeight * 0.5; };

// ---------------------------------------------------------------- the picture
// The reveal only moves forward: replaying or pressing play never re-hides the picture,
// and once it is fully revealed it stays still (no scan line, no highlights).
class View {
  constructor(canvas) { this.c = canvas; this.g = canvas.getContext("2d"); }

  set(img, score) {
    this.img = img; this.score = score; this.reveal = 0; this.revealed = false;
    this.c.width = img.naturalWidth; this.c.height = img.naturalHeight;
    // resolution levels for the reveal: the sonified grid itself, then 2x, 4x, 8x
    this.levels = [1, 2, 4, 8].map(k => {
      const w = score.cols * k, h = score.rows * k, o = document.createElement("canvas");
      o.width = w; o.height = h;
      const og = o.getContext("2d"); og.imageSmoothingQuality = "high"; og.drawImage(img, 0, 0, w, h);
      return o;
    });
    this.draw(-1, 0);
  }

  finish() { this.revealed = true; this.draw(); }

  draw(col = -1, frac = 0) {
    const { g, c, score } = this, W = c.width, H = c.height;
    g.imageSmoothingEnabled = false;
    if (this.revealed) { g.drawImage(this.img, 0, 0); return; }
    const cw = W / score.cols, ch = H / score.rows;
    const cursor = col < 0 ? 0 : (col + frac) * cw;
    const leading = cursor >= this.reveal - 0.5;           // the scan is uncovering new ground
    this.reveal = Math.max(this.reveal, cursor);
    const R = this.reveal;
    g.drawImage(this.levels[0], 0, 0, W, H);                // ahead: the raw grid, dimmed
    g.fillStyle = "rgba(5,6,10,.55)"; g.fillRect(R, 0, W - R, H);
    if (R > 0) {                                            // behind: sharper as the track goes on
      const lvl = this.levels[Math.min(3, Math.floor((R / W) * 4))];
      g.save(); g.beginPath(); g.rect(0, 0, R, H); g.clip();
      g.drawImage(lvl, 0, 0, W, H); g.restore();
    }
    if (col < 0 || !leading) return;
    const x0 = col * cw;                                   // steady colours: nothing pulses or flashes
    score.columns[col].notes.forEach(n => {
      if (n.row == null) return;                            // bass, chords, drums have no cell
      g.fillStyle = VOICES[n.voice].color; g.globalAlpha = 0.45;
      g.fillRect(x0, n.row * ch, cw, ch);
    });
    g.globalAlpha = 1;
    g.strokeStyle = "#ffb000"; g.lineWidth = Math.max(2, cw / 6);
    g.strokeRect(x0, 0, cw, H);
    g.fillStyle = "rgba(255,176,0,.9)"; g.fillRect(cursor - 1, 0, 2, H);
  }
}
const view = new View($("view"));
const turntable = new Turntable($("disc"), { reduced });

// ---------------------------------------------------------------- HUD
function buildBars() {
  $("bars").innerHTML = Object.entries(VOICES).map(([k, v]) =>
    `<div class="bar" style="--c:${v.color}"><span>${v.label}</span><span class="cells" data-v="${k}">${"<i></i>".repeat(8)}</span></div>`).join("");
  $("legend").innerHTML = Object.values(VOICES).map(v =>
    `<li style="--c:${v.color}"><span class="swatch"></span><span><b>${v.label}</b> · ${v.wave.toUpperCase().replace("PULSE25", "PULSE")}<br>${v.what}</span></li>`).join("");
}

function hud(i) {
  const col = track.score.columns[i];
  $("rCol").textContent = `${i + 1}/${track.score.cols}`;
  const top = leadNote(col);
  $("rNote").textContent = top ? noteName(top.midi) : "--";
  $("rChord").textContent = col.chord ? col.chord.split(" ")[0] : "--";
  const dv = dominantVoice(col);
  $("rVoice").textContent = dv ? VOICES[dv].label : "REST";
  const level = {};
  col.notes.forEach(n => { level[n.voice] = (level[n.voice] || 0) + n.vel; });
  document.querySelectorAll(".cells").forEach(el => {
    const lit = Math.round(Math.min(1, (level[el.dataset.v] || 0) / 2) * 8);
    [...el.children].forEach((c, j) => c.classList.toggle("on", j < lit));
  });
}

let lastCol = -1;
const player = new Player(chip, {
  onColumn(i, frac) {
    view.draw(i, frac);
    if (i !== lastCol) { lastCol = i; hud(i); }
  },
  onEnd() {
    view.finish();
    setPlayBtn(false);
    $("endmsg").hidden = false;
    chip.over();
    say("Track complete. Insert another coin for a new picture, or press R to replay.");
  },
});

function setPlayBtn(playing) {
  $("playBtn").textContent = playing ? "PAUSE" : "PLAY";
  $("playBtn").setAttribute("aria-pressed", String(playing));
  if (track && !selecting) turntable.setState(playing ? "play" : player.pos < track.score.columns.length ? "pause" : "ready");
}

// ---------------------------------------------------------------- tracks
async function prepare(item) {
  const img = await loadImage("images/" + item.file);
  const { cols, rows } = gridSize(img.naturalWidth, img.naturalHeight);
  const o = document.createElement("canvas"); o.width = cols; o.height = rows;
  const og = o.getContext("2d", { willReadFrequently: true });
  og.imageSmoothingQuality = "high"; og.drawImage(img, 0, 0, cols, rows);
  const grid = og.getImageData(0, 0, cols, rows);
  return { item, img, grid, score: score(grid) };
}

function score(grid) {
  const s = style === "melody" ? compose(grid, MAPPING) : sonify(grid, MAPPING);
  if (DEBUG && s.why) console.log(s.why, s.features);
  if (DEBUG) console.table(s.columns.map(c => ({ x: c.x, dur: +c.dur.toFixed(3), notes: c.notes.map(n => `${noteName(n.midi)}:${n.voice}`).join(" ") })));
  return s;
}

function changeKey(d) {
  keyIdx = (keyIdx + d + 12) % 12;
  applyKey(); store.set("key", KEY_NAMES[keyIdx]);
  if (!track) return;
  rescore();
  if (!player.playing) { chip.playColumn(track.score.columns[Math.min(player.pos, track.score.cols - 1)]); }
  say(`Key: ${KEY_NAMES[keyIdx].replace("#", " sharp")} ${modeWords(track.score)}.`);
}

function rescore() {                              // same picture, new score: keep the playhead
  track.score = score(track.grid);
  view.score = track.score;
  player.setScore(track.score);
  hud(Math.min(player.pos, track.score.cols - 1));
  showStyle();
}

function toggleStyle() {
  style = style === "melody" ? "raw" : "melody";
  store.set("style", style);
  if (track) rescore(); else showStyle();
  say(style === "melody"
    ? "Style: melody. Computer vision composes a song from the picture. " + (track?.score.why || "")
    : "Style: raw. Every pixel plays itself, column by column.");
}

// ---------------------------------------------------------------- records: choose like a real jukebox
const LETTERS = "ABCD";
const codeOf = i => LETTERS[Math.floor(i / 9)] + (i % 9 + 1);
let selecting = false, typed = "", countdownT = 0;

function buildBoard() {
  $("board").innerHTML = manifest.slice(0, 36).map((m, i) =>
    `<button class="strip" data-i="${i}" aria-label="${codeOf(i)}: ${esc(m.place)}. ${esc(m.title)}"><b>${codeOf(i)}</b><span>${esc(m.place.toUpperCase())}</span></button>`).join("");
  $("board").addEventListener("click", e => { const b = e.target.closest(".strip"); if (b) choose(+b.dataset.i); });
}
const markBoard = i => document.querySelectorAll(".strip").forEach(b => b.setAttribute("aria-current", String(+b.dataset.i === i)));

function showTyped() {
  $("typed").textContent = typed ? `${typed} _` : "_ _";
  document.querySelectorAll(".strip").forEach(b => b.classList.toggle("match", !!typed && codeOf(+b.dataset.i)[0] === typed));
}

function enterSelect() {
  player.stop(); setPlayBtn(false); turntable.setState("idle");
  selecting = true; typed = ""; showTyped();
  $("titlecard").classList.add("gone"); $("endmsg").hidden = true; $("selectcard").hidden = false;
  $("npCode").textContent = "--"; $("npName").textContent = "SELECT A RECORD";
  const d = chip.speak(voice.choose);
  say("Choose a record. Type a letter from A to D and a number from 1 to 9, or pick one from the list of records. If you do not choose, a surprise record plays in 8 seconds.");
  $("countdown").textContent = "SURPRISE RECORD IN 8";
  clearTimeout(countdownT);
  countdownT = setTimeout(() => countdown(8), d * 1000);
}

function countdown(left) {             // the number changes once a second: no flashing
  clearTimeout(countdownT);
  if (!selecting) return;
  $("countdown").textContent = `SURPRISE RECORD IN ${left}`;
  if (left <= 0) { choose(randomIndex()); return; }
  countdownT = setTimeout(() => countdown(left - 1), 1000);
}

function typeKey(k) {
  if (!selecting) { chip.blip(40); say("Insert another coin to choose a record."); $("again").focus(); return; }
  if (LETTERS.includes(k)) { typed = k; showTyped(); chip.blip(88); countdown(8); return; }
  if (!typed) { chip.blip(40); return; }
  const i = LETTERS.indexOf(typed) * 9 + (+k - 1);
  if (i >= manifest.length) { typed = ""; showTyped(); chip.blip(40); say("There is no record with that code."); return; }
  choose(i);
}

async function choose(i) {
  if (!selecting) { typeKey("?"); return; }
  selecting = false; clearTimeout(countdownT);
  chip.stopVoice(); chip.blip(96);
  $("selectcard").hidden = true; typed = ""; showTyped();
  markBoard(i); store.set("last", manifest[i].id);
  $("playBtn").focus({ preventScroll: true });     // so Space pauses instead of pressing a record
  try { await startTrack(await prepare(manifest[i])); }
  catch (e) { say("Could not load the picture."); console.error(e); }
}

async function startTrack(next) {
  player.stop();
  track = next; current = next.item;
  const i = manifest.indexOf(current), code = codeOf(i);
  $("trackno").textContent = `RECORD ${code}`;
  $("npCode").textContent = code; $("npName").textContent = current.place.toUpperCase();
  $("place").textContent = current.place;
  $("ttitle").textContent = current.title + (current.date ? ` · ${current.date.slice(0, 4)}` : "");
  $("view").setAttribute("aria-label", current.alt || current.title);
  $("cap").innerHTML = `${esc(current.title)}${current.date ? " (" + esc(current.date) + ")" : ""}. Image: ${esc(current.credit)} · ` +
    `<a href="${esc(current.source_url)}" target="_blank" rel="noopener">source</a>. Not endorsed by NASA.`;
  $("endmsg").hidden = true; $("titlecard").classList.remove("gone");
  lastCol = -1;
  view.set(next.img, next.score);
  player.load(next.score);
  showStyle();
  turntable.setState("ready");
  say(`Now playing record ${code}: ${current.place}. ${current.title}. ${current.alt || ""} ${next.score.why || ""}`);
  chip.jingle();
  await new Promise(r => setTimeout(r, reduced ? 600 : 1800));
  if (track !== next || selecting) return;             // another coin went in meanwhile
  $("titlecard").classList.add("gone");
  setCredit(Math.max(0, credits - 1));
  player.play(0); setPlayBtn(true);
}

const esc = s => String(s ?? "").replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

// ---------------------------------------------------------------- coin (Enter / Space)
const coin = $("coin");
async function insertCoin() {
  if (busy || !manifest.length) return;
  busy = true;
  chip.ensure();
  stopTour(); chip.stopAmbient(1.5);
  const drop = chip.coin();
  setCredit(credits + 1);
  await animateCoinIn();
  await new Promise(r => setTimeout(r, reduced ? 100 : drop * 600));
  const section = $("s-play");
  const first = section.hidden;
  section.hidden = false;
  if (window.ScrollTrigger) ScrollTrigger.refresh();
  section.scrollIntoView({ behavior: reduced || DEBUG ? "auto" : "smooth" });
  if (first) $("board").querySelector(".strip")?.focus({ preventScroll: true });
  resetCoin();
  busy = false;
  enterSelect();
}

function againCoin() {
  if (busy) return;
  chip.ensure(); chip.coin(); setCredit(credits + 1);
  setTimeout(enterSelect, 700);         // let the coin land before the voice speaks
}

function animateCoinIn() {
  const s = $("slot").getBoundingClientRect(), c = coin.getBoundingClientRect();
  const dx = s.left + s.width / 2 - (c.left + c.width / 2), dy = s.top + s.height / 2 - (c.top + c.height / 2);
  if (reduced || !window.gsap) { coin.style.opacity = "0"; return Promise.resolve(); }
  // the timeout keeps the flow moving if animation frames are paused (background tab)
  return new Promise(res => { setTimeout(res, 800); gsap.timeline({ onComplete: res })
    .to(coin, { x: dx, y: dy, duration: 0.25, ease: "power2.in" })
    .to(coin, { scaleX: 0.12, duration: 0.1, ease: "steps(3)" })
    .to(coin, { y: dy + 28, opacity: 0, duration: 0.18, ease: "steps(4)" }); });
}
function resetCoin() {
  if (window.gsap) gsap.set(coin, { clearProps: "transform,opacity" });
  coin.style.opacity = "";
}
if (touchOnly) {                     // phones have no Enter key: a tap on the coin is the fallback
  $("coinhelp").textContent = "TAP THE COIN";
  coin.addEventListener("click", () => started && insertCoin());
}

// ---------------------------------------------------------------- start (power-on)
async function start() {
  if (started) return;
  started = true;
  setSound(true);
  $("start").classList.add("gone");
  document.body.classList.remove("locked");
  // decoding needs the AudioContext, which may only be created now (after the key press)
  await Promise.all(Object.entries(voiceBytes).map(async ([n, p]) => {
    const bytes = await p;
    if (bytes) voice[n] = await chip.ensure().decodeAudioData(bytes).catch(() => null);
  }));
  chip.startAmbient();
  typewriter();
  const d = chip.speak(voice.welcome);
  await wait(d * 1000 + 600);
  if (!insertSaid && !busy) tour();         // not if they already went down to the coin
}

// ---------------------------------------------------------------- sound tour: the four elements
const ELEMENTS = [["triangle", "water", "BLUE"], ["pulse", "land", "GREEN, BROWN"], ["square", "fire", "RED, YELLOW"], ["noise", "wind", "WHITE, GREY"]];
const ICONS = {        // 8x8 pixel icons
  triangle: ["........", "..##....", ".#..#..#", "#....##.", "..##....", ".#..#..#", "#....##.", "........"],
  pulse:    ["........", "....#...", "...###..", "..#####.", ".#######", "########", "########", "........"],
  square:   ["...#....", "...##...", "..###.#.", "..#####.", ".######.", ".##..##.", "..#..#..", "........"],
  noise:    ["........", "#####...", ".....#..", "######..", "........", "###.....", "...#....", "........"],
};
const wait = ms => new Promise(r => setTimeout(r, ms));
let tourId = 0;

function buildElements() {
  $("elements").innerHTML = ELEMENTS.map(([k, , colours]) =>
    `<li data-v="${k}" style="--c:${VOICES[k].color}"><canvas width="8" height="8" aria-hidden="true"></canvas><b>${VOICES[k].label}</b><small>${colours}</small></li>`).join("");
  document.querySelectorAll("#elements li").forEach(li => {
    const g = li.querySelector("canvas").getContext("2d");
    g.fillStyle = VOICES[li.dataset.v].color;
    ICONS[li.dataset.v].forEach((row, y) => [...row].forEach((c, x) => c === "#" && g.fillRect(x, y, 1, 1)));
  });
}
const lightElement = k => document.querySelectorAll("#elements li").forEach(li => li.classList.toggle("on", li.dataset.v === k));

async function tour() {
  const me = ++tourId, alive = () => me === tourId && !busy;
  $("hearAgain").hidden = true;
  if (voice.elements) { await wait(chip.speak(voice.elements) * 1000 + 300); if (!alive()) return; }
  for (const [k, name] of ELEMENTS) {
    lightElement(k);
    say(`${VOICES[k].label}: ${VOICES[k].what}.`);
    if (voice[name]) { await wait(chip.speak(voice[name]) * 1000 + 150); if (!alive()) return; }
    await wait(chip.demo(k) * 1000 + 500); if (!alive()) return;
  }
  lightElement(null);
  ELEMENTS.forEach(([k]) => document.querySelector(`#elements li[data-v="${k}"]`).classList.add("on"));
  if (voice.discover) chip.speak(voice.discover);
  $("hearAgain").hidden = false;
}
function stopTour() { tourId++; chip.stopVoice(); }

// "insert a coin, press enter or space" the first time the coin screen comes into view
let insertSaid = false;
new IntersectionObserver(es => {
  if (!started || insertSaid || busy || !es.some(e => e.isIntersecting)) return;
  insertSaid = true;
  stopTour(); lightElement(null);
  chip.speak(voice.insert);
}, { threshold: 0.6 }).observe($("s-coin"));

// ---------------------------------------------------------------- controls
$("startBtn").onclick = start;
$("hearAgain").onclick = () => { chip.startAmbient(); tour(); };
$("mute").onclick = () => { setSound(!chip.on); if (chip.on) chip.blip(); };
$("playBtn").onclick = () => {
  if (!track || selecting) return;
  if (player.playing) { player.pause(); setPlayBtn(false); say("Paused. " + describeColumn(track.score.columns[player.pos], track.score.cols)); }
  else { $("endmsg").hidden = true; $("titlecard").classList.add("gone"); player.play(); setPlayBtn(true); }
};
$("replay").onclick = () => { if (!track || selecting) return; $("endmsg").hidden = true; $("titlecard").classList.add("gone"); player.play(0); setPlayBtn(true); };
$("again").onclick = againCoin;
$("keyUp").onclick = () => changeKey(1);
$("keyDown").onclick = () => changeKey(-1);
$("styleBtn").onclick = toggleStyle;
document.querySelectorAll("button").forEach(b => b.addEventListener("pointerenter", () => started && chip.on && chip.blip(96)));

document.addEventListener("keydown", e => {
  if (e.altKey || e.ctrlKey || e.metaKey) return;
  const k = e.key.toLowerCase(), enterOrSpace = e.key === "Enter" || e.key === " ";
  if (!started) { if (enterOrSpace) { e.preventDefault(); start(); } return; }
  if (k === "m") { $("mute").click(); return; }
  // Enter / Space: on the welcome screen go to the coin, on the coin screen insert it
  if (enterOrSpace && visible($("s-coin"))) { e.preventDefault(); insertCoin(); return; }
  if (enterOrSpace && e.target.tagName === "BUTTON") return;    // e.g. HEAR THE ELEMENTS AGAIN
  if (enterOrSpace && visible($("s-attract"))) {
    e.preventDefault(); $("s-coin").scrollIntoView({ behavior: reduced ? "auto" : "smooth" }); return;
  }
  if ($("s-play").hidden) return;
  if (/^[a-d1-9]$/.test(k)) { e.preventDefault(); typeKey(k.toUpperCase()); return; }
  if (e.key === "+" || e.key === "=") { changeKey(1); return; }
  if (e.key === "-" || e.key === "_") { changeKey(-1); return; }
  if (k === "v") { toggleStyle(); return; }
  if (!track || selecting) return;
  if (e.key === " " && e.target.tagName !== "BUTTON" && e.target.tagName !== "SUMMARY") { e.preventDefault(); $("playBtn").click(); }
  else if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
    e.preventDefault();
    player.step(e.key === "ArrowRight" ? 1 : -1); setPlayBtn(false); $("titlecard").classList.add("gone");
    say(describeColumn(track.score.columns[player.pos], track.score.cols));
  }
  else if (k === "r") $("replay").click();
  else if (k === "n") $("again").click();
});

// ---------------------------------------------------------------- scroll story
function typewriter() {
  const h = $("welcome"), text = h.dataset.text;
  if (reduced) return;
  h.setAttribute("aria-label", text);
  h.textContent = ""; h.classList.add("cursor");
  let i = 0;
  const t = setInterval(() => { h.textContent = text.slice(0, ++i); if (i >= text.length) { clearInterval(t); setTimeout(() => h.classList.remove("cursor"), 1200); } }, 80);
}

function scrollStory() {
  if (!window.gsap || !window.ScrollTrigger || reduced) return;
  gsap.registerPlugin(ScrollTrigger);
  gsap.to(".attract", { opacity: 0, ease: "none",
    scrollTrigger: { trigger: "#s-attract", start: "top top", end: "bottom top", scrub: true } });
  gsap.from(".coinbox > *", { y: 30, opacity: 0, stagger: 0.12, ease: "none",
    scrollTrigger: { trigger: "#s-coin", start: "top 85%", end: "top 25%", scrub: true } });
}

// ---------------------------------------------------------------- boot
// fetch the clips straight away so they are ready when START is pressed
const voiceBytes = Object.fromEntries(["welcome", "insert", "elements", "water", "land", "fire", "wind", "discover", "choose"].map(n =>
  [n, fetch(`voice/${n}.wav`).then(r => (r.ok ? r.arrayBuffer() : null)).catch(() => null)]));

async function boot() {
  drawCoin(); drawSlot(); buildBars(); buildElements(); scrollStory(); showStyle();
  try {
    const r = await fetch("images/manifest.json");
    manifest = await r.json();
    if (!manifest.length) throw new Error("empty manifest");
    buildBoard();
    const earth = manifest.find(m => m.id.startsWith("epic"));   // the record label: the whole Earth
    if (earth) loadImage("images/" + earth.file).then(img => turntable.setEarth(img, 0.8)).catch(() => {});
  } catch (e) {
    $("loadmsg").hidden = false;
    $("loadmsg").textContent = location.protocol === "file:"
      ? "OPEN THIS PAGE THROUGH A LOCAL SERVER: cd arcade; python -m http.server 8000"
      : "NO PICTURES FOUND. RUN: python backend/scripts/fetch_arcade_images.py";
  }
  if (DEBUG) window.__ej = { chip, voice, player, view, get track() { return track; } };
  if (DEBUG && params.has("coin")) { $("startBtn").click(); insertCoin(); }   // dev: skip to the track
}
boot();
