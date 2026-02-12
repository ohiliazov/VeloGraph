export enum BikeCategory {
  ROAD = "road",
  MOUNTAIN = "mountain",
  GRAVEL = "gravel",
  TOURING = "touring",
  HYBRID = "hybrid",
  CITY = "city",
  KIDS = "kids",
  OTHER = "other",
}

export enum MaterialGroup {
  CARBON = "carbon",
  ALUMINUM = "aluminum",
  STEEL = "steel",
  TITANIUM = "titanium",
  OTHER = "other",
}

export interface GeometrySpec {
  id: number;
  definition_id: number;
  size_label: string;
  stack_mm: number;
  reach_mm: number;
  top_tube_effective_mm: number | null;
  seat_tube_length_mm: number | null;
  head_tube_length_mm: number | null;
  head_tube_angle: number;
  seat_tube_angle: number;
  chainstay_length_mm: number;
  wheelbase_mm: number;
  bb_drop_mm: number;
  fork_offset_mm: number | null;
  trail_mm: number | null;
  standover_height_mm: number | null;
  definition?: BikeDefinition;
}

export interface BikeDefinition {
  id: number;
  brand_name: string;
  model_name: string;
  category: string;
  simple_categories: BikeCategory[];
  simple_material: MaterialGroup | null;
  year_start: number | null;
  year_end: number | null;
  material: string | null;
  geometries?: GeometrySpec[];
}

export interface BikeFamily {
  id: number;
  brand_name: string;
  family_name: string;
  category: string;
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
  geometry_spec: GeometrySpec;
  build_kit: BuildKit;
}

export interface BikeGroup {
  definition: BikeDefinition;
  products: BikeProduct[];
}

export interface Geometry {
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

export interface Bike {
  id: number;
  brand: string;
  model_name: string;
  model_year: number;
  categories: string[];
  geometries: Geometry[];
  color?: string;
  frame_material?: string;
  wheel_size?: string;
  brake_type?: string;
  max_tire_width?: number;
  source_url?: string;
}

export interface SearchResult {
  total: number;
  items: GeometrySpec[];
}

export interface GroupedSearchResult {
  total: number;
  items: BikeDefinition[];
}
