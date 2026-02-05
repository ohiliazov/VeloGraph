from __future__ import annotations

import math
import re
from pathlib import Path

import svgwrite
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.db import SessionLocal
from backend.core.models import BikeGeometryORM, BikeMetaORM
from backend.scripts.constants import artifacts_dir

# --- Geometry rendering helpers ---
FRAME_COLOR = "blue"
FRAME_TUBE_WIDTH = 30  # mm visual thickness
WHEEL_DIAMETER_MM = 622  # 700c default
TIRE_WIDTH_MM = 30
RIM_DEPTH_MM = 45
MARGIN_PX = 20
SCALE = 0.4  # px per mm


def sanitize_filename(value: str) -> str:
    s = value.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unnamed"


def compute_points(geom: BikeGeometryORM) -> dict[str, tuple[float, float]]:
    # Inputs from DB are already in mm/degrees according to ORM
    stack_mm = geom.stack
    reach_mm = geom.reach
    bb_drop_mm = geom.bb_drop
    chainstay_mm = geom.chainstay_length
    seat_tube_mm = geom.seat_tube_length
    seat_tube_angle = geom.seat_tube_angle
    head_tube_mm = geom.head_tube_length
    head_tube_angle = geom.head_tube_angle
    wheelbase_mm = geom.wheelbase

    bb = (0.0, -float(bb_drop_mm))
    rear_axle = (-float(chainstay_mm), 0.0)
    front_axle = (float(wheelbase_mm - chainstay_mm), 0.0)

    seat_top = (
        -seat_tube_mm * math.cos(math.radians(seat_tube_angle)),
        seat_tube_mm * math.sin(math.radians(seat_tube_angle)),
    )

    head_top = (float(reach_mm), float(stack_mm - bb_drop_mm))
    head_bottom = (
        head_top[0] + head_tube_mm * math.cos(math.radians(head_tube_angle)),
        head_top[1] - head_tube_mm * math.sin(math.radians(head_tube_angle)),
    )

    return {
        "bb": bb,
        "rear_axle": rear_axle,
        "front_axle": front_axle,
        "seat_top": seat_top,
        "head_top": head_top,
        "head_bottom": head_bottom,
    }


def compute_canvas(points: dict[str, tuple[float, float]]) -> tuple[int, int, float, float]:
    wheel_radius = (WHEEL_DIAMETER_MM + TIRE_WIDTH_MM) / 2

    xs = [
        points["rear_axle"][0] - wheel_radius,
        points["front_axle"][0] + wheel_radius,
        points["seat_top"][0],
        points["head_top"][0],
        points["head_bottom"][0],
    ]
    ys = [
        points["rear_axle"][1] - wheel_radius,
        points["rear_axle"][1] + wheel_radius,
        points["seat_top"][1],
        points["head_top"][1],
        points["head_bottom"][1],
        points["bb"][1],
    ]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width_mm = max_x - min_x
    height_mm = max_y - min_y

    svg_w = int(width_mm * SCALE + 2 * MARGIN_PX)
    svg_h = int(height_mm * SCALE + 2 * MARGIN_PX)

    tx = MARGIN_PX - SCALE * min_x
    ty = MARGIN_PX + SCALE * max_y
    return svg_w, svg_h, tx, ty


def render_svg(meta: BikeMetaORM, geom: BikeGeometryORM, out_path: Path) -> None:
    points = compute_points(geom)
    svg_w, svg_h, tx, ty = compute_canvas(points)

    dwg = svgwrite.Drawing(str(out_path), size=(f"{svg_w}px", f"{svg_h}px"))
    g = dwg.g(transform=f"translate({tx},{ty}) scale({SCALE},-{SCALE})")

    wheel_r = (WHEEL_DIAMETER_MM + TIRE_WIDTH_MM) / 2
    rim_r = (WHEEL_DIAMETER_MM - RIM_DEPTH_MM) / 2

    # Wheels
    g.add(dwg.circle(center=points["rear_axle"], r=wheel_r, stroke="black", stroke_width=TIRE_WIDTH_MM, fill="none"))
    g.add(dwg.circle(center=points["rear_axle"], r=rim_r, stroke="grey", stroke_width=RIM_DEPTH_MM, fill="none"))
    g.add(dwg.circle(center=points["front_axle"], r=wheel_r, stroke="black", stroke_width=TIRE_WIDTH_MM, fill="none"))
    g.add(dwg.circle(center=points["front_axle"], r=rim_r, stroke="grey", stroke_width=RIM_DEPTH_MM, fill="none"))

    # Tubes
    g.add(dwg.circle(center=points["bb"], r=FRAME_TUBE_WIDTH // 2, fill=FRAME_COLOR))
    g.add(dwg.circle(center=points["rear_axle"], r=FRAME_TUBE_WIDTH // 2, fill=FRAME_COLOR))
    g.add(dwg.line(start=points["bb"], end=points["rear_axle"], stroke=FRAME_COLOR, stroke_width=FRAME_TUBE_WIDTH))

    g.add(dwg.circle(center=points["seat_top"], r=FRAME_TUBE_WIDTH // 2, fill=FRAME_COLOR))
    g.add(dwg.line(start=points["bb"], end=points["seat_top"], stroke=FRAME_COLOR, stroke_width=FRAME_TUBE_WIDTH))

    g.add(
        dwg.line(start=points["seat_top"], end=points["rear_axle"], stroke=FRAME_COLOR, stroke_width=FRAME_TUBE_WIDTH)
    )

    g.add(dwg.circle(center=points["head_bottom"], r=FRAME_TUBE_WIDTH // 2, fill=FRAME_COLOR))
    g.add(dwg.line(start=points["bb"], end=points["head_bottom"], stroke=FRAME_COLOR, stroke_width=FRAME_TUBE_WIDTH))

    g.add(dwg.circle(center=points["head_top"], r=FRAME_TUBE_WIDTH // 2, fill=FRAME_COLOR))
    g.add(dwg.line(start=points["seat_top"], end=points["head_top"], stroke=FRAME_COLOR, stroke_width=FRAME_TUBE_WIDTH))

    g.add(
        dwg.line(start=points["head_bottom"], end=points["head_top"], stroke=FRAME_COLOR, stroke_width=FRAME_TUBE_WIDTH)
    )

    g.add(dwg.circle(center=points["front_axle"], r=FRAME_TUBE_WIDTH // 2, fill=FRAME_COLOR))
    g.add(
        dwg.line(
            start=points["head_bottom"], end=points["front_axle"], stroke=FRAME_COLOR, stroke_width=FRAME_TUBE_WIDTH
        )
    )

    dwg.add(g)
    dwg.save()


def main() -> None:
    output_dir = artifacts_dir / "generated_svgs"
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    with SessionLocal() as session:
        stmt = select(BikeMetaORM).options(selectinload(BikeMetaORM.geometries))
        bikes = session.scalars(stmt).all()

        if not bikes:
            logger.warning("No bikes found in database; nothing to render.")
            return

        for bike in bikes:
            for geom in bike.geometries:
                brand = bike.brand or "unknown"
                model = bike.model_name or "model"
                size = geom.size_label or "size"
                fname = f"{sanitize_filename(brand)}_{sanitize_filename(model)}_{sanitize_filename(size)}.svg"
                out_path = output_dir / fname
                try:
                    render_svg(bike, geom, out_path)
                    count += 1
                    logger.debug("Rendered {} → {}", f"{brand} {model} [{size}]", out_path)
                except Exception:
                    logger.exception("Failed to render {} {} {}", brand, model, size)

    logger.success("Generated {} SVG files in {}", count, output_dir)


if __name__ == "__main__":
    main()
