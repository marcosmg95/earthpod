export interface TrackRef {
  id: string;
  label: string;
  dir: string;
  source: string;
  mapping?: string;
  start?: string;
  end?: string;
  manifest?: boolean;
  about?: string;
  scan?: { from: number; to: number };
}

export interface Chapter {
  id: string;
  num: string;
  short: string;
  title: string;
  kicker: string;
  logline: string;
  tracks: readonly TrackRef[];
}

const CO2 = {
  source: "NASA SVS 5196",
  start: "2020-01-14",
  end: "2020-03-02",
  about: "co2/svs5196_nasa_description",
  mapping:
    "Living Earth: lungs, heartbeat and regions.\n" +
    "Background: a centred soft breath (more tan haze on screen = louder; brighter while the haze grows, darker while it fades) and the CO₂ heartbeat (daily pulse of the orange-red area, panned by its position).\n" +
    "Foreground: one instrument per region, entering in pairs as the orbit brings it into view (Asia oboe + Oceania harp, Europe flute + Africa marimba, North America vibraphone + South America cello). Higher register = further north, left/right = west/east. Each instrument's pitch is the orange-red amount in its part of the screen (upper third for the northern region, lower two thirds for the southern one), ranked against that pair's time on screen (higher note = more than usual for that stretch). Timed for the orbit movie.\n" +
    "Data: colours measured from the NASA SVS 5196 movie (GEOS / DYAMOND model), not actual breathing, a heartbeat or CO₂ in ppm; camera and background affect these picture indices.",
};
const NIGHT = {
  source: "NASA SVS 5313",
  about: "nightlights/svs5313_nasa_description",
};
const AIR = {
  source: "NASA SVS 5669",
  about: "aerosols/svs5669_nasa_description",
  scan: { from: -180, to: 180 }, // the line runs west → east
};

export const CHAPTERS: readonly Chapter[] = [
  {
    id: "co2",
    num: "01",
    short: "Breathing planet",
    title: "The breathing planet",
    kicker: "CO₂ · January–March 2020 · model data",
    logline:
      "Three months of carbon dioxide over the whole planet, January to March 2020, from a NASA model. Listen to it breathe.",
    tracks: [
      {
        id: "heart-lungs",
        label: "Heart and lungs",
        dir: "co2/svs5196_co2_15_lungs_heart_region",
        ...CO2,
      },
    ],
  },
  {
    id: "nightlights",
    num: "02",
    short: "Night lights",
    title: "The night lights",
    kicker: "Night lights · 2012–2023 · VIIRS satellite",
    logline:
      "Twelve yearly maps of the Earth at night, 2012 to 2023, then what changed: purple where lights grew, orange where they dimmed.",
    tracks: [
      {
        id: "three-acts",
        label: "Change in night lights, 2012–2023",
        dir: "nightlights/svs5313_nightlights_three_acts",
        ...NIGHT,
      },
    ],
  },
  {
    id: "aerosols",
    num: "03",
    short: "Aerosols",
    title: "The air we share",
    kicker: "Aerosols · 19 August 2025 · GEOS model",
    logline:
      "One moment in August 2025: sulfate, dust, smoke and sea salt drifting around the planet. A line scans the map from west to east, and each kind of particle has its own sound.",
    tracks: [
      {
        id: "scan",
        label: "Aerosols around the world, 19 August 2025",
        dir: "aerosols/svs5669_aerosols_bands",
        ...AIR,
      },
    ],
  },
];

export interface NavItem {
  id: string;
  num?: string;
  short: string;
  href: string;
}

export const CHAPTER_NAV = [
  { id: "listen", num: "00", short: "How to listen", href: "/listen" },
  ...CHAPTERS.map((c) => ({
    id: c.id,
    num: c.num,
    short: c.short,
    href: `/${c.id}`,
  })),
];

export const MORE_NAV: readonly NavItem[] = [
  { id: "record", short: "Record", href: "/record" },
  { id: "accessibility", short: "Accessibility", href: "/accessibility" },
];

export const FIRST_CHAPTER = CHAPTERS[0].id;
