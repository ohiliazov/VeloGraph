"""increase_material_length_to_100

Revision ID: 7e62683efbc4
Revises: d30f598bc1c0
Create Date: 2026-02-10 12:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e62683efbc4"
down_revision: str | Sequence[str] | None = "d30f598bc1c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Increase frame_definitions.material length from 30 to 100
    op.alter_column(
        "frame_definitions",
        "material",
        existing_type=sa.String(length=30),
        type_=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert length back to 30
    op.alter_column(
        "frame_definitions",
        "material",
        existing_type=sa.String(length=100),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
