"""alter litter group add column coverage_area

Revision ID: f771ec85e613
Revises: 7021ff58fd02
Create Date: 2025-06-19 13:32:25.806653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# import Geometry from GeoAlchemy2, not from sqlalchemy.dialects.postgresql
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = 'f771ec85e613'
down_revision: Union[str, None] = '7021ff58fd02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add coverage_area polygon column."""
    op.add_column(
        'litter_groups',
        sa.Column(
            'coverage_area',
            Geometry(geometry_type='POLYGON', srid=4326),
            nullable=True,
            comment="Convex-hull polygon used to lock out future clustering"
        )
    )


def downgrade() -> None:
    """Downgrade schema: drop coverage_area column."""
    op.drop_column('litter_groups', 'coverage_area')
