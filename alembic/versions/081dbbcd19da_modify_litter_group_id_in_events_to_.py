"""modify litter_group_id in events to nullable and update group_status_enum

Revision ID: 081dbbcd19da
Revises: c55a911a1ff1
Create Date: 2025-07-26 18:12:07.408947
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "081dbbcd19da"
down_revision: Union[str, None] = "c55a911a1ff1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Make cleanup_events.litter_group_id nullable
    op.alter_column(
        "cleanup_events",
        "litter_group_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )

    # 2) Drop any existing default on litter_groups.status to avoid cast/default problems
    op.execute("ALTER TABLE litter_groups ALTER COLUMN status DROP DEFAULT")

    # 3) Convert the enum column to plain text so we can safely update string values
    op.execute("ALTER TABLE litter_groups ALTER COLUMN status TYPE TEXT USING status::text")

    # 4) Map old values -> new values (adjust mappings here if you desire different behavior)
    op.execute(
        """
        UPDATE litter_groups
        SET status = CASE
            WHEN status = 'inactive' THEN 'locked'
            WHEN status = 'banned' THEN 'archived'
            ELSE status
        END
        WHERE status IS NOT NULL
        """
    )

    # 5) Create the desired new enum type (temporary name)
    op.execute(
        "CREATE TYPE group_status_enum_new AS ENUM('active','locked','archived')"
    )

    # 6) Convert the column from text -> new enum (safe because values now match)
    op.execute(
        """
        ALTER TABLE litter_groups
        ALTER COLUMN status
        TYPE group_status_enum_new
        USING status::text::group_status_enum_new
        """
    )

    # 7) Re-add a default value
    op.execute("ALTER TABLE litter_groups ALTER COLUMN status SET DEFAULT 'active'")

    # 8) Drop old enum type if exists, and rename new enum to canonical name
    op.execute("DROP TYPE IF EXISTS group_status_enum")
    op.execute("ALTER TYPE group_status_enum_new RENAME TO group_status_enum")


def downgrade() -> None:
    # Reverse the upgrade steps

    # 1) Create old enum type under a temporary name
    op.execute("CREATE TYPE group_status_enum_old AS ENUM('active','inactive','banned')")

    # 2) Drop default so we can convert types
    op.execute("ALTER TABLE litter_groups ALTER COLUMN status DROP DEFAULT")

    # 3) Convert enum -> text so we can remap strings
    op.execute("ALTER TABLE litter_groups ALTER COLUMN status TYPE TEXT USING status::text")

    # 4) Map new enum values back to old values
    op.execute(
        """
        UPDATE litter_groups
        SET status = CASE
            WHEN status = 'locked' THEN 'inactive'
            WHEN status = 'archived' THEN 'banned'
            ELSE status
        END
        WHERE status IS NOT NULL
        """
    )

    # 5) Convert text -> old enum
    op.execute(
        """
        ALTER TABLE litter_groups
        ALTER COLUMN status
        TYPE group_status_enum_old
        USING status::text::group_status_enum_old
        """
    )

    # 6) Re-add previous default (adjust if original default was different)
    op.execute("ALTER TABLE litter_groups ALTER COLUMN status SET DEFAULT 'active'")

    # 7) Drop current canonical enum and rename old back to canonical name
    op.execute("DROP TYPE IF EXISTS group_status_enum")
    op.execute("ALTER TYPE group_status_enum_old RENAME TO group_status_enum")

    # 8) Revert cleanup_events.litter_group_id to non-nullable
    op.alter_column(
        "cleanup_events",
        "litter_group_id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
