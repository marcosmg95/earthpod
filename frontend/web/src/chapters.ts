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
};
const NIGHT = {
  source: "NASA SVS 5313",
  about: "nightlights/svs5313_nasa_description",
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
