from pydantic import BaseModel, Field, PositiveInt
from pprint import pprint


class BikeMeta(BaseModel):
    model_name: str
    brand: str
    category: str
    year: int | None
    wheel_size: str | None
    frame_material: str | None
    brake_type: str | None


class BikeGeometry(BaseModel):
    """
    Comprehensive Pydantic model for bicycle frameset geometry.
    Measurements are in millimeters (mm) and angles in degrees (°).
    """

    # --- Group 1: Rider Fit (The 'Box' the rider occupies) ---
    reach: PositiveInt = Field(
        description=(
            "The horizontal distance from the center of the Bottom Bracket to the center of the top of the head tube. "
            "Primary indicator of 'roominess' when standing."
        ),
    )
    stack: PositiveInt = Field(
        description=(
            "The vertical distance from the center of the Bottom Bracket to the center of the top of the head tube. "
            "Determines the minimum handlebar height."
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
            "Measured center-to-top or center-to-center. "
            "Limits seatpost insertion and determines standover height."
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
            "The total horizontal distance between the front and rear axles. "
            "Longer provides more high-speed stability."
        ),
    )

    class Config:
        populate_by_name = True  # Allows initialization using aliases (e.g., TT=540)


if __name__ == "__main__":
    data = {
        "S": {
            "reach": 371,
            "stack": 537,
            "TT": 520,
            "ST": 490,
            "HT": 120,
            "CS": 435,
            "HA": 70.5,
            "SA": 74.5,
            "bb_drop": 67,
            "WB": 1020,
        },
        "M": {
            "reach": 375,
            "stack": 557,
            "TT": 535,
            "ST": 520,
            "HT": 140,
            "CS": 435,
            "HA": 71,
            "SA": 74,
            "bb_drop": 67,
            "WB": 1027,
        },
        "L": {
            "reach": 376,
            "stack": 568,
            "TT": 550,
            "ST": 540,
            "HT": 150,
            "CS": 435,
            "HA": 71.5,
            "SA": 73,
            "bb_drop": 67,
            "WB": 1027,
        },
        "XL": {
            "reach": 385,
            "stack": 590,
            "TT": 565,
            "ST": 560,
            "HT": 170,
            "CS": 435,
            "HA": 72,
            "SA": 73,
            "bb_drop": 67,
            "WB": 1037,
        },
    }

    for item in data.values():
        pprint(BikeGeometry(**item))
