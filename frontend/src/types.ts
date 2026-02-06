export enum BikeCategory {
  GRAVEL = "gravel",
  MTB = "mtb",
  TREKKING = "trekking",
  CROSS = "cross",
  ROAD = "road",
  CITY = "city",
  KIDS = "kids",
  TOURING = "touring",
  WOMEN = "women",
  OTHER = "other",
}

export enum MaterialGroup {
  CARBON = "carbon",
  ALUMINUM = "aluminum",
  STEEL = "steel",
  TITANIUM = "titanium",
  OTHER = "other",
}

export interface Frameset {
  id: number;
  name: string;
  material: string | null;
  category: string;
  size_label: string;
  stack: number;
  reach: number;
  top_tube_effective_length: number;
  seat_tube_length: number;
  head_tube_length: number;
  chainstay_length: number;
  head_tube_angle: number;
  seat_tube_angle: number;
  bb_drop: number;
  wheelbase: number;
}

export interface BuildKit {
  id: number;
  name: string;
  groupset: string | null;
  wheelset: string | null;
  cockpit: string | null;
  tires: string | null;
}

export interface BikeProduct {
  id: number;
  sku: string;
  colors: string[];
  source_url: string | null;
  frameset: Frameset;
  build_kit: BuildKit;
}

export interface BikeGroup {
  frameset_name: string;
  material: string | null;
  build_kit: BuildKit;
  products: BikeProduct[];
}

export interface SearchResult {
  total: number;
  items: BikeProduct[];
}

export interface GroupedSearchResult {
  total: number;
  items: BikeGroup[];
}
