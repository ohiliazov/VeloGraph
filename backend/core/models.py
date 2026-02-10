from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# 1. The High-Level Family (Brand + Model Family)
# Example: Specialized Tarmac, Trek Madone
class BikeFamilyORM(Base):
    __tablename__ = "bike_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    family_name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Tarmac", "Grizl"
    category: Mapped[str] = mapped_column(String(30), nullable=False)  # Road, Gravel, MTB

    # One Family has many Generations/Definitions
    definitions: Mapped[list[FrameDefinitionORM]] = relationship(back_populates="family", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("brand_name", "family_name", name="_brand_family_uc"),)


# 2. The Specific Generation (Year + Frame Type)
# Example: Tarmac SL8 (2024), Grizl CF SL (2022)
# This replaces your 'FramesetORM' + 'BikeModelORM' mix
class FrameDefinitionORM(Base):
    __tablename__ = "frame_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("bike_families.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "SL8", "Gen 7", "CF SL"
    year_start: Mapped[int] = mapped_column(Integer, nullable=True)  # Useful for "2022-2024" ranges
    year_end: Mapped[int] = mapped_column(Integer, nullable=True)
    material: Mapped[str] = mapped_column(String(100), nullable=True)  # Carbon, Alloy

    family: Mapped[BikeFamilyORM] = relationship(back_populates="definitions")

    # One Frame Definition has MANY Geometry Sizes
    geometries: Mapped[list[GeometrySpecORM]] = relationship(back_populates="definition", cascade="all, delete-orphan")


# 3. The Geometry Data (The "God-Tier" Data)
# Example: Size 54, Size 56, Size L
class GeometrySpecORM(Base):
    __tablename__ = "geometry_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("frame_definitions.id", ondelete="CASCADE"), nullable=False)

    size_label: Mapped[str] = mapped_column(String(20), nullable=False)  # 54, L, S3

    # --- FIT METRICS (The Searchable Core) ---
    stack_mm: Mapped[int] = mapped_column(nullable=False, index=True)
    reach_mm: Mapped[int] = mapped_column(nullable=False, index=True)

    # --- HANDLING METRICS ---
    top_tube_effective_mm: Mapped[int] = mapped_column(nullable=True)
    seat_tube_length_mm: Mapped[int] = mapped_column(nullable=True)
    head_tube_length_mm: Mapped[int] = mapped_column(nullable=True)
    head_tube_angle: Mapped[float] = mapped_column(nullable=False)
    seat_tube_angle: Mapped[float] = mapped_column(nullable=False)
    chainstay_length_mm: Mapped[int] = mapped_column(nullable=False)
    wheelbase_mm: Mapped[int] = mapped_column(nullable=False)
    bb_drop_mm: Mapped[int] = mapped_column(nullable=False)

    # --- ADVANCED GEO (God-Tier Extras) ---
    fork_offset_mm: Mapped[int] = mapped_column(nullable=True)  # Rake
    trail_mm: Mapped[int] = mapped_column(nullable=True)  # Calculated or scraped
    standover_height_mm: Mapped[int] = mapped_column(nullable=True)

    definition: Mapped[FrameDefinitionORM] = relationship(back_populates="geometries")
