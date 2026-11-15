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

// TODO: confirm both meanings with the data team
export const BODY: Sample[] = [
  {
    id: "breath",
    file: `${base}sample_00_breath.wav`,
    title: "Breath",
    instrument: "Breath",
    meaning: "The planet breathing: the slow rise and fall under every scene.",
  },
  {
    id: "heart",
    file: `${base}sample_01_heart.wav`,
    title: "Heart",
    instrument: "Heartbeat",
    meaning: "A heartbeat that keeps time as the days go by.",
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
]
