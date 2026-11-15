export type Sample = {
  id: string;
  file: string;
  title: string;
  instrument: string;
  meaning: string;
  lon?: number;
  lat?: number;
};

const base = "data/samples/";

export const BODY: Sample[] = [
  {
    id: "breath",
    file: `${base}sample_00_breath.wav`,
    title: "Breath",
    instrument: "Breath",
    meaning: "louder when there is more CO₂ haze on screen",
  },
  {
    id: "heart",
    file: `${base}sample_01_heart.wav`,
    title: "Heart",
    instrument: "Heartbeat",
    meaning: "one beat per day, from the densest CO₂",
  },
];

const continent = (
  n: string,
  id: string,
  title: string,
  instrument: string,
  lon: number,
  lat: number,
): Sample => ({
  id,
  file: `${base}sample_${n}_${id}_${instrument.toLowerCase()}.wav`,
  title,
  instrument,
  meaning: `Plays while ${title} is on screen.`,
  lon,
  lat,
});

export const CONTINENTS: Sample[] = [
  // left column, top to bottom
  continent("04", "europe", "Europe", "Flute", 15, 50),
  continent("06", "north_america", "North America", "Vibraphone", -100, 45),
  continent("07", "south_america", "South America", "Cello", -60, -15),
  // right column, top to bottom
  continent("02", "asia", "Asia", "Oboe", 90, 40),
  continent("05", "africa", "Africa", "Marimba", 20, 5),
  continent("03", "oceania", "Oceania", "Harp", 135, -25),
];

const one = (
  file: string,
  id: string,
  title: string,
  meaning: string,
): Sample => ({
  id,
  file: `${base}${file}.wav`,
  title,
  instrument: title,
  meaning,
});

export const NIGHT_SAMPLES: Sample[] = [
  one(
    "sample_nightlights_01_city_lights_plucks",
    "n-city",
    "City lights",
    "soft plucks, one sweep across the map per year",
  ),
  one(
    "sample_nightlights_02_brighter_than_2012_bells",
    "n-brighter",
    "Brighter than in 2012",
    "bells on top of the plucks",
  ),
  one(
    "sample_nightlights_03_new_lights_high_bells",
    "n-new",
    "New lights",
    "high bells for the purple on the change map",
  ),
  one(
    "sample_nightlights_04_lights_out_low_plucks",
    "n-out",
    "Lights out",
    "low plucks for the orange on the change map",
  ),
  one(
    "sample_nightlights_05_weur_pluck",
    "n-weur",
    "Western Europe",
    "a pluck for its zoom box",
  ),
  one(
    "sample_nightlights_06_emed_soft",
    "n-emed",
    "Eastern Mediterranean",
    "a soft tone for its zoom box",
  ),
  one(
    "sample_nightlights_07_ukr_bell",
    "n-ukr",
    "Ukraine",
    "a bell for its zoom box",
  ),
  one(
    "sample_nightlights_08_ind_pluck",
    "n-ind",
    "India",
    "a pluck for its zoom box",
  ),
];

export const AIR_SAMPLES: Sample[] = [
  one(
    "sample_aerosols_01_sulfate_hum",
    "a-sulfate",
    "Sulfate",
    "a smooth hum (green on the map)",
  ),
  one(
    "sample_aerosols_02_dust_grains",
    "a-dust",
    "Dust",
    "sand grains (pink on the map)",
  ),
  one(
    "sample_aerosols_03_smoke_crackle",
    "a-smoke",
    "Smoke",
    "a crackle (orange-red)",
  ),
  one("sample_aerosols_04_sea_salt_surf", "a-salt", "Sea salt", "surf (blue)"),
  one(
    "sample_aerosols_05_plume_chime",
    "a-chime",
    "Big plume",
    "a glass chime where a large plume begins",
  ),
  one(
    "sample_aerosols_06_haze_wind",
    "a-wind",
    "Haze",
    "a soft wind under everything",
  ),
  one(
    "sample_aerosols_07_meridian_ticks",
    "a-ticks",
    "Longitude",
    "a tick every 30°, deeper at Greenwich",
  ),
];
