from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# 1. The High-Level Family (Brand + Model)
# Example: Specialized Tarmac, Trek Madone
class BikeDefinitionORM(Base):
    __tablename__ = "bike_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_name: Mapped[str] = mapped_column(nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    year_start: Mapped[int] = mapped_column(nullable=True)
    year_end: Mapped[int] = mapped_column(nullable=True)
    material: Mapped[str] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("brand_name", "model_name", name="_brand_model_uc"),)

    # One Frame Definition has MANY Geometry Sizes
    geometries: Mapped[list[GeometrySpecORM]] = relationship(back_populates="definition", cascade="all, delete-orphan")


# 3. The Geometry Data (The "God-Tier" Data)
# Example: Size 54, Size 56, Size L
class GeometrySpecORM(Base):
    __tablename__ = "geometry_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("bike_definitions.id", ondelete="CASCADE"), nullable=False)

    size_label: Mapped[str] = mapped_column(nullable=False)

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
    fork_offset_mm: Mapped[int] = mapped_column(nullable=True)
    trail_mm: Mapped[int] = mapped_column(nullable=True)
    standover_height_mm: Mapped[int] = mapped_column(nullable=True)

    definition: Mapped[BikeDefinitionORM] = relationship(back_populates="geometries")
