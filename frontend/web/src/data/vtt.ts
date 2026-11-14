export interface Cue {
  start: number;
  end: number;
  text: string;
}

function seconds(s: string): number {
  const p = s.trim().split(":").map(Number);
  return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p[0] * 60 + p[1];
}

export function parseVtt(src: string): Cue[] {
  const cues: Cue[] = [];
  for (const block of src.replace(/\r/g, "").split(/\n\n+/)) {
    const lines = block.split("\n");
    const i = lines.findIndex((l) => l.includes("-->"));
    if (i < 0) continue;
    const [a, b] = lines[i].split("-->");
    cues.push({
      start: seconds(a),
      end: seconds(b.trim().split(/\s+/)[0]),
      text: lines
        .slice(i + 1)
        .join(" ")
        .trim(),
    });
  }
  return cues;
}
