import math
import re
from dataclasses import dataclass

import svgwrite

# --- Constants ---

DEFAULT_JOINTS = {
    "topToSeatDrop": 0.08,
    "topToHeadDrop": 0.07,
    "downToHeadRise": 0.1,
}

DEFAULT_FRAME_COLOR = "#2563eb"  # blue-600
WHEEL_COLOR = "#94a3b8"  # slate-400
FRAME_TUBE_WIDTH = 25
DEFAULT_WHEEL_DIAMETER_MM = 622
DEFAULT_TIRE_WIDTH_MM = 30
RIM_DEPTH_MM = 30
MARGIN_PX = 10
SCALE = 0.35

WHEEL_SIZE_MAP: dict[str, int] = {
    "700": 622,
    "584": 584,
    "559": 559,
    "507": 507,
    "406": 406,
    "305": 305,
    "254": 254,
    "203": 203,
    "29": 622,
    "28": 622,
    "27.5": 584,
    "26": 559,
    "24": 507,
    "20": 406,
    "16": 305,
    "14": 254,
    "12": 203,
}

COLOR_MAP: dict[str, str] = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ef4444",
    "blue": "#3b82f6",
    "green": "#22c55e",
    "gray": "#6b7280",
    "silver": "#9ca3af",
    "gold": "#eab308",
    "orange": "#f97316",
    "yellow": "#facc15",
    "purple": "#a855f7",
    "pink": "#ec4899",
    "brown": "#92400e",
    "navy": "#1e3a8a",
    "teal": "#0d9488",
    # Add other PL/EN mappings as needed
}

# --- Types ---


@dataclass
class GeometrySpec:
    stack_mm: float
    reach_mm: float
    bb_drop_mm: float
    chainstay_length_mm: float
    wheelbase_mm: float
    seat_tube_length_mm: float | None = None
    seat_tube_angle: float | None = None
    head_tube_length_mm: float | None = None
    head_tube_angle: float | None = None


# --- Helpers ---


def normalize_color(input_str: str | None) -> str:
    if not input_str:
        return DEFAULT_FRAME_COLOR
    s = str(input_str).strip()

    # 1) Hex code check
    hex_match = re.search(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", s)
    if hex_match:
        return hex_match.group(0)

    lower = s.lower()

    # 2) Token mapping
    tokens = re.split(r"[\s,/\-]+", lower)
    for tok in tokens:
        if tok in COLOR_MAP:
            return COLOR_MAP[tok]

    return s


def generate_bike_svg(
    geometry: GeometrySpec,
    wheel_size: str | None = None,
    max_tire_width: str | None = None,
    width: int | None = None,
    height: int | None = None,
    show_wheels: bool = True,
    frame_color: str | None = None,
    joint_adjustments: dict[str, float] | None = None,
) -> str:
    # 1. Inputs & Defaults
    stack = geometry.stack_mm
    reach = geometry.reach_mm
    bb_drop = geometry.bb_drop_mm
    chainstay = geometry.chainstay_length_mm
    wheelbase = geometry.wheelbase_mm

    seat_tube = geometry.seat_tube_length_mm or 500
    seat_angle = geometry.seat_tube_angle or 73.0
    head_tube = geometry.head_tube_length_mm or 150
    head_angle = geometry.head_tube_angle or 73.0

    wheel_diameter = WHEEL_SIZE_MAP.get(str(wheel_size), DEFAULT_WHEEL_DIAMETER_MM)
    tire_width = float(max_tire_width) if max_tire_width else DEFAULT_TIRE_WIDTH_MM

    # 2. Compute Points (Math coordinates)
    rad_sa = math.radians(seat_angle)
    rad_ha = math.radians(head_angle)

    head_top = (reach, stack - bb_drop)
    head_bottom = (
        head_top[0] + head_tube * math.cos(rad_ha),
        head_top[1] - head_tube * math.sin(rad_ha),
    )

    points = {
        "bb": (0, -bb_drop),
        "rear_axle": (-chainstay, 0),
        "front_axle": (wheelbase - chainstay, 0),
        "seat_top": (
            -seat_tube * math.cos(rad_sa),
            seat_tube * math.sin(rad_sa) - bb_drop,
        ),
        "head_top": head_top,
        "head_bottom": head_bottom,
    }

    # 3. ViewBox Calculation
    wheel_radius = (wheel_diameter + tire_width) / 2

    xs = [
        points["rear_axle"][0] - (wheel_radius if show_wheels else 0),
        points["front_axle"][0] + (wheel_radius if show_wheels else 0),
        points["seat_top"][0],
        points["head_top"][0],
        points["head_bottom"][0],
        points["bb"][0],
    ]
    ys = [
        points["rear_axle"][1] - (wheel_radius if show_wheels else 0),
        points["rear_axle"][1] + (wheel_radius if show_wheels else 0),
        points["seat_top"][1],
        points["head_top"][1],
        points["head_bottom"][1],
        points["bb"][1],
        0,  # Axle line
    ]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width_mm = max(max_x - min_x, 1)
    height_mm = max(max_y - min_y, 1)

    # Scale Logic
    current_scale = SCALE
    available_w = (width - 2 * MARGIN_PX) if width else 0
    available_h = (height - 2 * MARGIN_PX) if height else 0

    if width and height:
        current_scale = min(available_w / width_mm, available_h / height_mm)
    elif width:
        current_scale = available_w / width_mm
    elif height:
        current_scale = available_h / height_mm

    current_scale = max(current_scale, 0.01)

    svg_w = width if width else (width_mm * current_scale + 2 * MARGIN_PX)
    svg_h = height if height else (height_mm * current_scale + 2 * MARGIN_PX)

    # 4. Initialize SVG Drawing
    dwg = svgwrite.Drawing(size=(svg_w, svg_h), profile="tiny")
    dwg.viewbox(0, 0, svg_w, svg_h)

    # Transformation Logic
    offset_x = (svg_w - width_mm * current_scale - 2 * MARGIN_PX) / 2
    offset_y = (svg_h - height_mm * current_scale - 2 * MARGIN_PX) / 2
    tx = MARGIN_PX + offset_x - min_x * current_scale
    ty = MARGIN_PX + offset_y + max_y * current_scale

    def to_svg(pt: tuple[float, float]) -> tuple[float, float]:
        return (tx + pt[0] * current_scale, ty - pt[1] * current_scale)

    # 5. Joint Math
    J = DEFAULT_JOINTS.copy()
    if joint_adjustments:
        J.update(joint_adjustments)

    # Vector helpers
    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])

    def add(a, b):
        return (a[0] + b[0], a[1] + b[1])

    def mul(v, s):
        return (v[0] * s, v[1] * s)

    def norm(v):
        L = math.hypot(v[0], v[1]) or 1
        return (v[0] / L, v[1] / L)

    u_seat = norm(sub(points["seat_top"], points["bb"]))
    u_head = norm(sub(points["head_top"], points["head_bottom"]))

    p_bb = to_svg(points["bb"])
    p_rear = to_svg(points["rear_axle"])
    p_front = to_svg(points["front_axle"])
    p_seat_top = to_svg(points["seat_top"])
    p_head_top = to_svg(points["head_top"])
    p_head_bottom = to_svg(points["head_bottom"])

    p_seat_joint = to_svg(add(points["seat_top"], mul(u_seat, -J["topToSeatDrop"] * seat_tube)))
    p_head_top_joint = to_svg(add(points["head_top"], mul(u_head, -J["topToHeadDrop"] * head_tube)))
    p_head_bot_joint = to_svg(add(points["head_bottom"], mul(u_head, J["downToHeadRise"] * head_tube)))

    # 6. Styling Dimensions
    wheel_r_px = ((wheel_diameter + tire_width) / 2) * current_scale
    rim_r_px = ((wheel_diameter - RIM_DEPTH_MM) / 2) * current_scale
    tire_w_px = tire_width * current_scale
    rim_w_px = RIM_DEPTH_MM * current_scale
    tube_w_px = max(FRAME_TUBE_WIDTH * current_scale, 1.5)

    final_frame_color = normalize_color(frame_color)

    # 7. Drawing Elements

    # Wheels
    if show_wheels:
        for center in [p_rear, p_front]:
            # Tire
            dwg.add(dwg.circle(center=center, r=wheel_r_px, stroke="#1e293b", stroke_width=tire_w_px, fill="none"))
            # Rim
            dwg.add(dwg.circle(center=center, r=rim_r_px, stroke=WHEEL_COLOR, stroke_width=rim_w_px, fill="none"))

    # Frame Tubes
    # Helper for tubes
    def add_tube(start, end):
        dwg.add(
            dwg.line(start=start, end=end, stroke=final_frame_color, stroke_width=tube_w_px, stroke_linecap="round")
        )

    add_tube(p_bb, p_rear)  # Chainstay
    add_tube(p_bb, p_seat_top)  # Seat Tube
    add_tube(p_seat_joint, p_rear)  # Seat Stay
    add_tube(p_bb, p_head_bot_joint)  # Down Tube
    add_tube(p_seat_joint, p_head_top_joint)  # Top Tube
    add_tube(p_head_bottom, p_head_top)  # Head Tube
    add_tube(p_head_bottom, p_front)  # Fork

    # Joints (Circles to smooth connections)
    def add_joint(center):
        dwg.add(dwg.circle(center=center, r=tube_w_px / 2, fill=final_frame_color))

    add_joint(p_bb)
    add_joint(p_seat_joint)
    add_joint(p_head_top_joint)
    add_joint(p_head_bot_joint)

    # Return SVG string
    return dwg.tostring()
