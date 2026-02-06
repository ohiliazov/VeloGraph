import sqlalchemy as sa
from pydantic import BaseModel, Field, PositiveInt
from sqlalchemy import ForeignKey
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


class FramesetORM(Base):
    __tablename__ = "framesets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    material: Mapped[str | None]
    size_label: Mapped[str] = mapped_column(nullable=False)

    stack: Mapped[int] = mapped_column(nullable=False)
    reach: Mapped[int] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(nullable=False, server_default="other")
    top_tube_effective_length: Mapped[int] = mapped_column(nullable=False)
    seat_tube_length: Mapped[int] = mapped_column(nullable=False)
    head_tube_length: Mapped[int] = mapped_column(nullable=False)
    chainstay_length: Mapped[int] = mapped_column(nullable=False)
    head_tube_angle: Mapped[float] = mapped_column(nullable=False)
    seat_tube_angle: Mapped[float] = mapped_column(nullable=False)
    bb_drop: Mapped[int] = mapped_column(nullable=False)
    wheelbase: Mapped[int] = mapped_column(nullable=False)

    bike_products: Mapped[list[BikeProductORM]] = relationship(back_populates="frameset")


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
    frameset_id: Mapped[int] = mapped_column(ForeignKey("framesets.id"), nullable=False)
    build_kit_id: Mapped[int] = mapped_column(ForeignKey("build_kits.id"), nullable=False)
    source_url: Mapped[str | None] = mapped_column(sa.String(1024))

    frameset: Mapped[FramesetORM] = relationship(back_populates="bike_products")
    build_kit: Mapped[BuildKitORM] = relationship(back_populates="bike_products")
