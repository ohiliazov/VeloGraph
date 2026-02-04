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
  model_year?: number;
  color?: string;
  categories: string[];
  wheel_size?: string;
  frame_material?: string;
  brake_type?: string;
  source_url?: string;
  max_tire_width?: string;
  geometries: Geometry[];
}

export interface SearchResult {
  total: number;
  items: Bike[];
}
