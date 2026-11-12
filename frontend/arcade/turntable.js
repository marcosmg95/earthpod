// The planetary record player: a vinyl whose label is a pixelated photo of the whole Earth
// (NASA EPIC), with a tone arm. Calm by design: the record turns slowly (one turn per 30 s)
// and only while music plays; with "reduce motion" it never turns and the arm moves instantly.

const TURN_SECONDS = 30;
const ARM_REST = -0.08, ARM_PLAY = 0.45;   // radians: off the record / head on the grooves

export class Turntable {
  constructor(canvas, { reduced = false } = {}) {
    this.c = canvas; this.g = canvas.getContext("2d");
    this.reduced = reduced;
    this.angle = 0; this.arm = ARM_REST; this.armTarget = ARM_REST;
    this.spinning = false; this.last = 0; this.raf = 0;
    this.label = null;
    this.draw();
  }

  // img: a full-disk Earth photo; `disc` = diameter of the planet as a fraction of the frame
  setEarth(img, disc = 0.8) {
    const px = 40;                                        // label resolution: chunky pixels
    const small = document.createElement("canvas"); small.width = small.height = px;
    const sg = small.getContext("2d");
    const s = Math.min(img.naturalWidth, img.naturalHeight) * disc;
    sg.imageSmoothingQuality = "high";
    sg.drawImage(img, (img.naturalWidth - s) / 2, (img.naturalHeight - s) / 2, s, s, 0, 0, px, px);
    // bake the pixel look into a large texture; rotating that (smoothly) does not shimmer
    const big = document.createElement("canvas"); big.width = big.height = px * 12;
    const bg = big.getContext("2d"); bg.imageSmoothingEnabled = false;
    bg.drawImage(small, 0, 0, big.width, big.height);
    this.label = big;
    this.draw();
  }

  // state: "idle" | "ready" | "play" | "pause"
  setState(state) {
    this.armTarget = state === "play" || state === "pause" ? ARM_PLAY : ARM_REST;
    this.spinning = state === "play" && !this.reduced;
    if (this.reduced) this.arm = this.armTarget;
    this.kick();
  }

  kick() { if (!this.raf) { this.last = performance.now(); this.raf = requestAnimationFrame(t => this.frame(t)); } }

  frame(t) {
    const dt = Math.min(0.1, (t - this.last) / 1000); this.last = t;
    if (this.spinning) this.angle = (this.angle + dt * 2 * Math.PI / TURN_SECONDS) % (2 * Math.PI);
    const d = this.armTarget - this.arm;
    this.arm += Math.abs(d) < 0.002 ? d : d * Math.min(1, dt * 5);
    this.draw();
    this.raf = this.spinning || this.arm !== this.armTarget ? requestAnimationFrame(n => this.frame(n)) : 0;
  }

  draw() {
    const { g, c } = this, W = c.width, H = c.height, cx = W * 0.44, cy = H * 0.5, R = W * 0.4;
    g.clearRect(0, 0, W, H);
    // plinth
    g.fillStyle = "#11141c"; g.fillRect(0, 0, W, H);
    g.strokeStyle = "#2a2f40"; g.lineWidth = W / 80; g.strokeRect(g.lineWidth / 2, g.lineWidth / 2, W - g.lineWidth, H - g.lineWidth);
    // vinyl with grooves (static rings: only the label shows the turn)
    g.fillStyle = "#050608"; g.beginPath(); g.arc(cx, cy, R, 0, 7); g.fill();
    g.strokeStyle = "rgba(255,255,255,.07)"; g.lineWidth = 1.5;
    for (let r = R * 0.5; r < R * 0.97; r += R * 0.045) { g.beginPath(); g.arc(cx, cy, r, 0, 7); g.stroke(); }
    g.strokeStyle = "rgba(62,199,255,.12)"; g.lineWidth = R * 0.05;          // soft sheen
    g.beginPath(); g.arc(cx, cy, R * 0.75, -2.4, -1.6); g.stroke();
    // the Earth label
    const L = R * 0.42;
    g.save(); g.translate(cx, cy); g.rotate(this.angle);
    g.beginPath(); g.arc(0, 0, L, 0, 7); g.clip();
    if (this.label) { g.imageSmoothingEnabled = true; g.drawImage(this.label, -L, -L, 2 * L, 2 * L); }
    else { g.fillStyle = "#2f7dd8"; g.fillRect(-L, -L, 2 * L, 2 * L); }
    g.restore();
    g.strokeStyle = "#ffb000"; g.lineWidth = W / 160; g.beginPath(); g.arc(cx, cy, L, 0, 7); g.stroke();
    g.fillStyle = "#f4f1ea"; g.beginPath(); g.arc(cx, cy, W / 90, 0, 7); g.fill();       // spindle
    // tone arm
    const px = W * 0.88, py = H * 0.14, len = H * 0.62;
    g.fillStyle = "#2a2f40"; g.beginPath(); g.arc(px, py, W * 0.06, 0, 7); g.fill();
    g.save(); g.translate(px, py); g.rotate(this.arm);
    g.fillStyle = "#c9ced9"; g.fillRect(-W / 120, 0, W / 60, len);
    g.fillStyle = "#ffb000"; g.fillRect(-W / 40, len - W / 60, W / 20, W / 14);           // head shell
    g.restore();
    g.fillStyle = "#f4f1ea"; g.beginPath(); g.arc(px, py, W * 0.025, 0, 7); g.fill();
  }
}
