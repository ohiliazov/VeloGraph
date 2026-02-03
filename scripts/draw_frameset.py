import math

import svgwrite

# Bike Geometry
frame_tube_width = 30
stack_mm = 590
reach_mm = 385
bb_drop_mm = 67
chainstay_mm = 435
seat_tube_mm = 560
seat_tube_angle = 73
head_tube_mm = 170
head_tube_angle = 72
wheelbase_mm = 1037
wheel_diameter_mm = 622
tire_width_mm = 30
rim_depth_mm = 65

# Coordinates
bb_coords = (0, -bb_drop_mm)
rear_axle_coords = (-chainstay_mm, 0)
front_axle_coords = (wheelbase_mm - chainstay_mm, 0)

seat_tube_coords = (
    -seat_tube_mm * math.cos(math.radians(seat_tube_angle)),
    seat_tube_mm * math.sin(math.radians(seat_tube_angle)),
)

head_tube_top_coords = (reach_mm, stack_mm - bb_drop_mm)

head_tube_bottom_coords = (
    head_tube_top_coords[0] + head_tube_mm * math.cos(math.radians(head_tube_angle)),
    head_tube_top_coords[1] - head_tube_mm * math.sin(math.radians(head_tube_angle)),
)

# COMPUTE SVG SIZE
wheel_radius = (wheel_diameter_mm + tire_width_mm) / 2

xs = [
    rear_axle_coords[0] - wheel_radius,
    front_axle_coords[0] + wheel_radius,
    seat_tube_coords[0],
    head_tube_top_coords[0],
    head_tube_bottom_coords[0],
]

ys = [
    rear_axle_coords[1] - wheel_radius,
    rear_axle_coords[1] + wheel_radius,
    seat_tube_coords[1],
    head_tube_top_coords[1],
    head_tube_bottom_coords[1],
    bb_coords[1],
]

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

width_mm = max_x - min_x
height_mm = max_y - min_y

MARGIN_PX = 20
SCALE = 0.4

SVG_WIDTH = int(width_mm * SCALE + 2 * MARGIN_PX)
SVG_HEIGHT = int(height_mm * SCALE + 2 * MARGIN_PX)

tx = MARGIN_PX - SCALE * min_x
ty = MARGIN_PX + SCALE * max_y

dwg = svgwrite.Drawing("esker.svg", size=(f"{SVG_WIDTH}px", f"{SVG_HEIGHT}px"))

# Geometry group:
# - center canvas
# - scale mm → px
# - flip Y axis
g = dwg.g(transform=f"translate({tx},{ty}) scale({SCALE},-{SCALE})")

# Wheels
g.add(
    dwg.circle(
        center=rear_axle_coords,
        r=(wheel_diameter_mm + tire_width_mm) / 2,
        stroke="black",
        stroke_width=tire_width_mm,
        fill="none",
    )
)
g.add(
    dwg.circle(
        center=rear_axle_coords,
        r=(wheel_diameter_mm - rim_depth_mm) / 2,
        stroke="grey",
        stroke_width=rim_depth_mm,
        fill="none",
    )
)
g.add(
    dwg.circle(
        center=front_axle_coords,
        r=(wheel_diameter_mm + tire_width_mm) / 2,
        stroke="black",
        stroke_width=tire_width_mm,
        fill="none",
    )
)
g.add(
    dwg.circle(
        center=front_axle_coords,
        r=(wheel_diameter_mm - rim_depth_mm) / 2,
        stroke="grey",
        stroke_width=rim_depth_mm,
        fill="none",
    )
)

# Chain stay tube
g.add(dwg.circle(center=bb_coords, r=frame_tube_width // 2, fill="red"))
g.add(dwg.circle(center=rear_axle_coords, r=frame_tube_width // 2, fill="red"))
g.add(
    dwg.line(
        start=bb_coords,
        end=rear_axle_coords,
        stroke="red",
        stroke_width=frame_tube_width,
    )
)

# Seat tube
g.add(dwg.circle(center=seat_tube_coords, r=frame_tube_width // 2, fill="red"))
g.add(
    dwg.line(
        start=bb_coords,
        end=seat_tube_coords,
        stroke="red",
        stroke_width=frame_tube_width,
    )
)

# Seat stay tube
g.add(
    dwg.line(
        start=seat_tube_coords,
        end=rear_axle_coords,
        stroke="red",
        stroke_width=frame_tube_width,
    )
)

# Down tube
g.add(dwg.circle(center=head_tube_bottom_coords, r=frame_tube_width // 2, fill="red"))
g.add(
    dwg.line(
        start=bb_coords,
        end=head_tube_bottom_coords,
        stroke="red",
        stroke_width=frame_tube_width,
    )
)

# Top tube
g.add(dwg.circle(center=head_tube_top_coords, r=frame_tube_width // 2, fill="red"))
g.add(
    dwg.line(
        start=seat_tube_coords,
        end=head_tube_top_coords,
        stroke="red",
        stroke_width=frame_tube_width,
    )
)

# Head tube
g.add(
    dwg.line(
        start=head_tube_bottom_coords,
        end=head_tube_top_coords,
        stroke="red",
        stroke_width=frame_tube_width,
    )
)

# Fork
g.add(dwg.circle(center=front_axle_coords, r=frame_tube_width // 2, fill="red"))
g.add(
    dwg.line(
        start=head_tube_bottom_coords,
        end=front_axle_coords,
        stroke="red",
        stroke_width=frame_tube_width,
    )
)

dwg.add(g)
dwg.save()
