from __future__ import annotations

import sqlalchemy as sa
from pydantic import BaseModel, Field, PositiveInt
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class GeometryData(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    stack: PositiveInt = Field(
        description=(
            "The vertical distance from the center of the Bottom Bracket to the center of the top of the head tube. "
            "Determines the minimum handlebar height."
        ),
    )
    reach: PositiveInt = Field(
        description=(
            "The horizontal distance from the center of the Bottom Bracket to the center of the top of the head tube. "
            "Primary indicator of 'roominess' when standing."
        ),
    )
    top_tube_effective_length: PositiveInt = Field(
        alias="TT",
        description=(
            "The horizontal distance from the head tube/top tube junction to the seat post. "
            "Defines how the bike feels when seated."
        ),
    )

    seat_tube_length: PositiveInt = Field(
        alias="ST",
        description=(
            "Measured center-to-top or center-to-center. Limits seatpost insertion and determines standover height."
        ),
    )
    head_tube_length: PositiveInt = Field(
        alias="HT",
        description="Physical length of the head tube. Affects stack and front-end stiffness.",
    )
    chainstay_length: PositiveInt = Field(
        alias="CS",
        description="The distance from the BB center to the rear axle. Shorter is snappier; longer is more stable.",
    )

    head_tube_angle: float = Field(
        ge=60.0,
        le=75.0,
        alias="HA",
        description="Angle relative to horizontal. Slack (lower) is stable; steep (higher) is agile/twitchy.",
    )
    seat_tube_angle: float = Field(
        ge=70.0,
        le=80.0,
        alias="SA",
        description="Angle relative to horizontal. Steep angles (75°+) help with climbing and power transfer.",
    )

    bb_drop: PositiveInt = Field(
        description=(
            "How far the BB center sits below the horizontal line connecting the axles. "
            "Lower drop increases stability in corners."
        ),
    )
    wheelbase: PositiveInt = Field(
        alias="WB",
        description=(
            "The total horizontal distance between the front and rear axles. Longer provides more high-speed stability."
        ),
    )


class Frameset(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    name: str
    material: str | None = None
    category: str = "other"
    size_label: str
    stack: PositiveInt
    reach: PositiveInt
    top_tube_effective_length: PositiveInt = Field(alias="TT")
    seat_tube_length: PositiveInt = Field(alias="ST")
    head_tube_length: PositiveInt = Field(alias="HT")
    chainstay_length: PositiveInt = Field(alias="CS")
    head_tube_angle: float = Field(ge=60.0, le=75.0, alias="HA")
    seat_tube_angle: float = Field(ge=70.0, le=80.0, alias="SA")
    bb_drop: PositiveInt
    wheelbase: PositiveInt = Field(alias="WB")


class BuildKit(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    name: str
    groupset: str | None = None
    wheelset: str | None = None
    cockpit: str | None = None
    tires: str | None = None


class BikeProduct(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    sku: str
    frameset_id: int
    build_kit_id: int


class Base(DeclarativeBase):
    pass


class BikeFamilyORM(Base):
    __tablename__ = "bike_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    family_name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "Tarmac", "Grizl"
    category: Mapped[str] = mapped_column(String(255), nullable=False)  # Road, Gravel, MTB

    # One Family has many Generations/Definitions
    definitions: Mapped[list[FrameDefinitionORM]] = relationship(back_populates="family", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("brand_name", "family_name", name="_brand_family_uc"),)


class FrameDefinitionORM(Base):
    __tablename__ = "frame_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("bike_families.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(512), nullable=False)  # e.g. "SL8", "Gen 7", "CF SL"
    year_start: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Useful for "2022-2024" ranges
    year_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    material: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # Carbon, Alloy

    family: Mapped[BikeFamilyORM] = relationship(back_populates="definitions")

    # One Frame Definition has MANY Geometry Sizes
    geometries: Mapped[list[GeometrySpecORM]] = relationship(back_populates="definition", cascade="all, delete-orphan")


class GeometrySpecORM(Base):
    __tablename__ = "geometry_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("frame_definitions.id", ondelete="CASCADE"), nullable=False)

    size_label: Mapped[str] = mapped_column(String(20), nullable=False)  # 54, L, S3

    # --- FIT METRICS (The Searchable Core) ---
    stack_mm: Mapped[int] = mapped_column(nullable=False, index=True)
    reach_mm: Mapped[int] = mapped_column(nullable=False, index=True)

    # --- HANDLING METRICS ---
    top_tube_effective_mm: Mapped[int | None] = mapped_column(nullable=True)
    seat_tube_length_mm: Mapped[int | None] = mapped_column(nullable=True)
    head_tube_length_mm: Mapped[int | None] = mapped_column(nullable=True)
    head_tube_angle: Mapped[float] = mapped_column(nullable=False)
    seat_tube_angle: Mapped[float] = mapped_column(nullable=False)
    chainstay_length_mm: Mapped[int] = mapped_column(nullable=False)
    wheelbase_mm: Mapped[int] = mapped_column(nullable=False)
    bb_drop_mm: Mapped[int] = mapped_column(nullable=False)

    # --- ADVANCED GEO (God-Tier Extras) ---
    fork_offset_mm: Mapped[int | None] = mapped_column(nullable=True)  # Rake
    trail_mm: Mapped[int | None] = mapped_column(nullable=True)  # Calculated or scraped
    standover_height_mm: Mapped[int | None] = mapped_column(nullable=True)

    definition: Mapped[FrameDefinitionORM] = relationship(back_populates="geometries")
    bike_products: Mapped[list[BikeProductORM]] = relationship(back_populates="geometry_spec")

    __table_args__ = (UniqueConstraint("definition_id", "size_label", name="_def_size_uc"),)


class BuildKitORM(Base):
    __tablename__ = "build_kits"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    groupset: Mapped[str | None]
    wheelset: Mapped[str | None]
    cockpit: Mapped[str | None]
    tires: Mapped[str | None]

    bike_products: Mapped[list[BikeProductORM]] = relationship(back_populates="build_kit")


class BikeProductORM(Base):
    __tablename__ = "bike_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(unique=True, nullable=False)
    colors: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, server_default="[]")
    geometry_spec_id: Mapped[int] = mapped_column(ForeignKey("geometry_specs.id", ondelete="CASCADE"), nullable=False)
    build_kit_id: Mapped[int] = mapped_column(ForeignKey("build_kits.id", ondelete="CASCADE"), nullable=False)
    source_url: Mapped[str | None] = mapped_column(sa.String(1024))

    geometry_spec: Mapped[GeometrySpecORM] = relationship(back_populates="bike_products")
    build_kit: Mapped[BuildKitORM] = relationship(back_populates="bike_products")

    __table_args__ = (UniqueConstraint("geometry_spec_id", "build_kit_id", name="_geo_bk_uc"),)
