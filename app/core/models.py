from pydantic import BaseModel, Field, PositiveInt
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BikeMeta(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    brand: str
    category: str
    model_name: str
    model_year: int | None
    wheel_size: str | None
    frame_material: str | None
    brake_type: str | None


class BikeGeometry(BaseModel):
    """
    Comprehensive Pydantic model for bicycle frameset geometry.
    Measurements are in millimeters (mm) and angles in degrees (°).
    """

    model_config = {"populate_by_name": True, "from_attributes": True}

    # --- Group 1: Rider Fit (The 'Box' the rider occupies) ---
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

    # --- Group 2: Frame Tubes (Physical dimensions) ---
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

    # --- Group 3: Chassis Angles (The 'Soul' of the handling) ---
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

    # --- Group 4: Positioning & Footprint ---
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


class Base(DeclarativeBase):
    pass


class BikeMetaORM(Base):
    __tablename__ = "bike_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str]
    category: Mapped[str]
    model_name: Mapped[str]
    model_year: Mapped[int | None]
    wheel_size: Mapped[str | None]
    frame_material: Mapped[str | None]
    brake_type: Mapped[str | None]


class BikeGeometryORM(Base):
    __tablename__ = "bike_geometry"

    id: Mapped[int] = mapped_column(primary_key=True)
    stack: Mapped[int] = mapped_column(nullable=False)
    reach: Mapped[int] = mapped_column(nullable=False)
    top_tube_effective_length: Mapped[int] = mapped_column(nullable=False)
    seat_tube_length: Mapped[int] = mapped_column(nullable=False)
    head_tube_length: Mapped[int] = mapped_column(nullable=False)
    chainstay_length: Mapped[int] = mapped_column(nullable=False)
    head_tube_angle: Mapped[float] = mapped_column(nullable=False)
    seat_tube_angle: Mapped[float] = mapped_column(nullable=False)
    bb_drop: Mapped[int] = mapped_column(nullable=False)
    wheelbase: Mapped[int] = mapped_column(nullable=False)
