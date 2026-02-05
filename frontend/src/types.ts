export interface Frameset {
  id: number;
  name: string;
  material: string | null;
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
  items: BikeGroup[];
}
