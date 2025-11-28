from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1e9521b854f7'
down_revision: Union[str, None] = '10c7c5144e3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum names
OLD_STATUS_ENUM = 'eventjoinstatus'
NEW_STATUS_ENUM = 'eventjoinstatus_new'


def upgrade() -> None:
    # --- CleanupEvent: add needs_approval column ---
    op.add_column(
        'cleanup_events',
        sa.Column('needs_approval', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    # remove temporary default
    op.alter_column('cleanup_events', 'needs_approval', server_default=None)

    # --- EventJoin: update status enum ---
    # create new enum type without 'withdrawn'
    op.execute(
        f"CREATE TYPE {NEW_STATUS_ENUM} AS ENUM('pending','approved','rejected')"
    )
    # drop existing default to avoid cast error
    op.alter_column(
        'event_join', 'status',
        existing_type=sa.Enum(name=OLD_STATUS_ENUM),
        server_default=None
    )
    # change column type via text cast
    op.alter_column(
        'event_join', 'status',
        type_=sa.Enum('pending','approved','rejected', name=NEW_STATUS_ENUM),
        postgresql_using=f"status::text::{NEW_STATUS_ENUM}",
        existing_nullable=False
    )
    # set new default
    op.alter_column(
        'event_join', 'status',
        server_default=sa.text(f"'approved'::{NEW_STATUS_ENUM}")
    )
    # drop old and rename new
    op.execute(f"DROP TYPE {OLD_STATUS_ENUM}")
    op.execute(f"ALTER TYPE {NEW_STATUS_ENUM} RENAME TO {OLD_STATUS_ENUM}")

    # --- EventJoin: drop withdrawn_at column ---
    op.drop_column('event_join', 'withdrawn_at')

    # --- EventJoin: add auto_approved column ---
    op.add_column(
        'event_join',
        sa.Column('auto_approved', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('event_join', 'auto_approved', server_default=None)


def downgrade() -> None:
    # --- Revert EventJoin: remove auto_approved ---
    op.drop_column('event_join', 'auto_approved')

    # --- Revert EventJoin: re-add withdrawn_at ---
    op.add_column(
        'event_join',
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True)
    )

    # --- Revert status enum back to include withdrawn ---
    op.execute(
        f"CREATE TYPE {OLD_STATUS_ENUM}_old AS ENUM('pending','approved','rejected','withdrawn')"
    )
    op.alter_column(
        'event_join', 'status',
        existing_type=sa.Enum(name=OLD_STATUS_ENUM),
        type_=sa.Enum('pending','approved','rejected','withdrawn', name=f"{OLD_STATUS_ENUM}_old"),
        postgresql_using=f"status::text::{OLD_STATUS_ENUM}_old",
        existing_nullable=False
    )
    op.alter_column(
        'event_join', 'status',
        server_default=sa.text(f"'pending'::{OLD_STATUS_ENUM}_old")
    )
    op.execute(f"DROP TYPE {OLD_STATUS_ENUM}")
    op.execute(f"ALTER TYPE {OLD_STATUS_ENUM}_old RENAME TO {OLD_STATUS_ENUM}")

    # --- Revert CleanupEvent: drop needs_approval ---
    op.drop_column('cleanup_events', 'needs_approval')
