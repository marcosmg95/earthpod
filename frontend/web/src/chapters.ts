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
    "Underneath: a soft breath that grows louder when there is more tan haze on screen, and a heartbeat, one beat per model day, from the densest orange-red areas.\n" +
    "On top: one instrument per region, entering in pairs as the globe turns: Asia oboe and Oceania harp, then Europe flute and Africa marimba, then North America vibraphone and South America cello. Northern regions sound higher; west and east come from the left and right. A higher note means more orange-red than usual in that region.\n" +
    "These sounds follow colours measured in NASA's SVS 5196 movie (GEOS / DYAMOND model). They are not real breathing, a real heartbeat or CO₂ measured in ppm.",
};
const NIGHT = {
  source: "NASA SVS 5313",
  about: "nightlights/svs5313_nasa_description",
  mapping:
    "Years: each year is one left-to-right sweep of soft plucks. Left is west, right is east, higher notes are further north, and louder means brighter. Bells mark places brighter than in 2012.\n" +
    "Change map: high bells for the purple (new lights), low plucks for the orange (lights out), then both together.\n" +
    "Zoom boxes: Western Europe, the Eastern Mediterranean, Ukraine and India each have their own instrument and side of the stereo field.\n" +
    "These sounds follow brightness and colours measured in NASA's SVS 5313 movie (Black Marble, 2012–2023). They are not calibrated light measurements.",
};
const AIR = {
  source: "NASA SVS 5669",
  about: "aerosols/svs5669_nasa_description",
  mapping:
    "A line scans the map from west to east, and the sound moves from left to right with it. Each 10° band of latitude has its own note, higher further north.\n" +
    "Each kind of particle has its own sound: sulfate hums, dust sounds like sand grains, smoke crackles and sea salt sounds like surf. Louder means more than usual for that band. A glass chime marks the largest plumes, a soft wind is all the haze together, and a tick sounds every 30° of longitude, deeper at Greenwich.\n" +
    "These sounds follow colours measured in NASA's SVS 5669 image (GEOS model, 19 August 2025, 20:00 UTC). They are not measured concentrations.",
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
