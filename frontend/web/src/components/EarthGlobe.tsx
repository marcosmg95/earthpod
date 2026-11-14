import { useEffect, useRef } from "react";
import { geoEquirectangular, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import landUrl from "world-atlas/land-110m.json?url";

type Props = {
  spinning?: boolean;
  /** degrees per second */
  speed?: number;
  /** turn to face this place, then rest */
  focusLon?: number;
  focusLat?: number;
  /** no easing (reduced motion) */
  instant?: boolean;
  className?: string;
};

const DEG = Math.PI / 180;
const TILT = 23.4 * DEG;
const SAMPLES = 40000;
const MASK_W = 1024;
const MASK_H = 512;
const LEVELS = 6;

/** shared by every globe, so the intro's Earth and the chapters' Earth line up */
const rotation = { current: 0 };
const tilt = { current: TILT };

type Points = { land: Float32Array; sea: Float32Array }; // [cosLat, sinLat, lon] triples

let pointsPromise: Promise<Points> | null = null;

/** Real coastlines → a land mask → evenly spaced land and sea dots. Built once, shared. */
function loadPoints(): Promise<Points> {
  pointsPromise ??= (async () => {
    const res = await fetch(landUrl);
    const topo = (await res.json()) as Topology<{ land: GeometryCollection }>;
    const land = feature(topo, topo.objects.land);

    const mask = document.createElement("canvas");
    mask.width = MASK_W;
    mask.height = MASK_H;
    const mctx = mask.getContext("2d", { willReadFrequently: true });
    if (!mctx) throw new Error("no 2d context");
    const projection = geoEquirectangular()
      .scale(MASK_W / (2 * Math.PI))
      .translate([MASK_W / 2, MASK_H / 2]);
    mctx.fillStyle = "#fff";
    mctx.beginPath();
    geoPath(projection, mctx)(land);
    mctx.fill();
    const px = mctx.getImageData(0, 0, MASK_W, MASK_H).data;

    const landPts: number[] = [];
    const seaPts: number[] = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < SAMPLES; i++) {
      const y = 1 - (2 * (i + 0.5)) / SAMPLES;
      const lat = Math.asin(y);
      const lon =
        ((((i * golden) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) -
        Math.PI;
      const mx = Math.min(
        MASK_W - 1,
        Math.floor(((lon + Math.PI) / (2 * Math.PI)) * MASK_W),
      );
      const my = Math.min(
        MASK_H - 1,
        Math.floor(((Math.PI / 2 - lat) / Math.PI) * MASK_H),
      );
      if (px[(my * MASK_W + mx) * 4] > 127) landPts.push(Math.cos(lat), y, lon);
      else if (i % 5 === 0) seaPts.push(Math.cos(lat), y, lon);
    }
    return { land: new Float32Array(landPts), sea: new Float32Array(seaPts) };
  })();
  return pointsPromise;
}

function parseRgb(color: string): [number, number, number] {
  const n = color.match(/[\d.]+/g)?.map(Number);
  if (!n || n.length < 3) return [94, 234, 212];
  const scale = color.startsWith("color(") ? 255 : 1;
  return [n[0] * scale, n[1] * scale, n[2] * scale];
}

/** shortest signed angle from a to b */
const turn = (a: number, b: number): number => {
  const d = (b - a) % (2 * Math.PI);
  return d > Math.PI ? d - 2 * Math.PI : d < -Math.PI ? d + 2 * Math.PI : d;
};

/** Decorative globe. Its colour comes from the CSS `color` of the canvas. */
export function EarthGlobe({
  spinning = true,
  speed = 12,
  focusLon,
  focusLat,
  instant = false,
  className,
}: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const parent = canvas?.parentElement;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !parent || !ctx) return;

    let points: Points | null = null;
    let rgb = parseRgb(getComputedStyle(canvas).color);
    let raf = 0;
    let last = 0;
    let stopped = false;
    const hasFocus = focusLon !== undefined && focusLat !== undefined;
    const targetRot = hasFocus ? -focusLon * DEG : 0;
    const targetTilt = hasFocus
      ? Math.max(-50, Math.min(50, focusLat)) * DEG
      : TILT;

    const rgba = (alpha: number) =>
      `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;

    const draw = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = parent.clientWidth;
      const h = parent.clientHeight;
      if (
        canvas.width !== Math.round(w * dpr) ||
        canvas.height !== Math.round(h * dpr)
      ) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const R = Math.min(w, h) * 0.44;
      const cx = w / 2;
      const cy = h / 2;
      if (R <= 0) return;

      const air = ctx.createRadialGradient(cx, cy, R * 0.96, cx, cy, R * 1.14);
      air.addColorStop(0, rgba(0.22));
      air.addColorStop(1, rgba(0));
      ctx.fillStyle = air;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.14, 0, 2 * Math.PI);
      ctx.fill();

      const body = ctx.createRadialGradient(
        cx - R * 0.4,
        cy - R * 0.4,
        R * 0.05,
        cx,
        cy,
        R,
      );
      body.addColorStop(0, rgba(0.14));
      body.addColorStop(1, rgba(0.02));
      ctx.fillStyle = body;
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, 2 * Math.PI);
      ctx.fill();

      if (!points) return;
      const rot = rotation.current;
      const ct = Math.cos(tilt.current);
      const st = Math.sin(tilt.current);
      const size = Math.max(1, R * 0.009);
      const half = size / 2;

      const project = (
        arr: Float32Array,
        each: (x: number, y: number, z: number) => void,
      ) => {
        for (let i = 0; i < arr.length; i += 3) {
          const cl = arr[i];
          const y0 = arr[i + 1];
          const lon = arr[i + 2] + rot;
          const x = cl * Math.sin(lon);
          const z0 = cl * Math.cos(lon);
          const z = z0 * ct + y0 * st;
          if (z <= 0) continue;
          each(x, y0 * ct - z0 * st, z);
        }
      };

      const sea = new Path2D();
      project(points.sea, (x, y) =>
        sea.rect(cx + x * R - half, cy - y * R - half, size, size),
      );
      ctx.fillStyle = rgba(1);
      ctx.globalAlpha = 0.07;
      ctx.fill(sea);

      const shades = Array.from({ length: LEVELS }, () => new Path2D());
      project(points.land, (x, y, z) => {
        const sun = Math.max(0, -0.51 * x + 0.51 * y + 0.69 * z);
        const level = 0.35 * z + 0.65 * sun;
        const b = Math.min(LEVELS - 1, Math.floor(level * LEVELS));
        shades[b].rect(cx + x * R - half, cy - y * R - half, size, size);
      });
      shades.forEach((path, b) => {
        ctx.globalAlpha = 0.25 + (0.75 * (b + 1)) / LEVELS;
        ctx.fill(path);
      });
      ctx.globalAlpha = 1;
    };

    const frame = (t: number) => {
      const dt = last ? (t - last) / 1000 : 0;
      last = t;
      let moving = spinning;
      if (hasFocus) {
        const dRot = turn(rotation.current, targetRot);
        const dTilt = targetTilt - tilt.current;
        const k = instant ? 1 : 1 - Math.exp(-dt * 3.5);
        rotation.current += dRot * k;
        tilt.current += dTilt * k;
        moving = Math.abs(dRot) > 0.001 || Math.abs(dTilt) > 0.001;
      } else if (spinning) {
        rotation.current += dt * speed * DEG;
      }
      draw();
      if (moving && !stopped) raf = requestAnimationFrame(frame);
    };

    const start = () => {
      if (stopped) return;
      if (spinning || hasFocus) raf = requestAnimationFrame(frame);
      else draw();
    };

    void loadPoints()
      .then((p) => {
        points = p;
        start();
      })
      .catch(() => start()); // no map data: still draws the glowing sphere

    const observer = new ResizeObserver(() => {
      rgb = parseRgb(getComputedStyle(canvas).color);
      draw();
    });
    observer.observe(parent);

    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [spinning, speed, focusLon, focusLat, instant]);

  return <canvas ref={ref} className={className} aria-hidden="true" />;
}
