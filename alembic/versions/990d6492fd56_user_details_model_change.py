"""user_details model change

Revision ID: 990d6492fd56
Revises: 417c9f6125a6
Create Date: 2025-06-12 23:53:37.410939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '990d6492fd56'
down_revision: Union[str, None] = '417c9f6125a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop old fields, add new user_details columns."""
    with op.batch_alter_table('user_details') as batch_op:
        # Drop obsolete columns
        batch_op.drop_column('address')
        batch_op.drop_column('latitude')
        batch_op.drop_column('longitude')
        batch_op.drop_column('preferences')
        batch_op.drop_column('created_by')
        batch_op.drop_column('updated_by')

        # Add new personal & profile fields
        batch_op.add_column(sa.Column('full_name', sa.String(length=150), nullable=False))
        batch_op.add_column(sa.Column('profile_photo', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('phone', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('social_links', postgresql.JSON(), nullable=True))
        batch_op.add_column(sa.Column('cleanup_types', postgresql.JSON(), nullable=True))
        batch_op.add_column(sa.Column('availability', postgresql.JSON(), nullable=True))
        batch_op.add_column(sa.Column('skills', postgresql.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema: restore old fields, remove new user_details columns."""
    with op.batch_alter_table('user_details') as batch_op:
        # Remove newly added columns
        batch_op.drop_column('skills')
        batch_op.drop_column('availability')
        batch_op.drop_column('cleanup_types')
        batch_op.drop_column('social_links')
        batch_op.drop_column('phone')
        batch_op.drop_column('profile_photo')
        batch_op.drop_column('full_name')

        # Recreate dropped columns
        batch_op.add_column(sa.Column('updated_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('preferences', postgresql.JSON(), nullable=True))
        batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('address', sa.String(length=255), nullable=False))
