"""create notifications table

Revision ID: 7add1142fbe1
Revises: 9a536882d7ed
Create Date: 2025-07-09 07:31:51.909047
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7add1142fbe1'
down_revision: Union[str, None] = '9a536882d7ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ENUM definitions
enums = {
    'notification_type': {
        'name': 'notification_type',
        'values': ['info', 'alert', 'reminder']
    }
}

def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Create ENUMs if not already present
    for e in enums.values():
        pg_enum = postgresql.ENUM(*e['values'], name=e['name'])
        pg_enum.create(bind=bind, checkfirst=True)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column(
            'id',
            sa.Integer,
            primary_key=True,
            nullable=False
        ),
        sa.Column(
            'user_id',
            sa.Integer,
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.Column(
            'message',
            sa.Text,
            nullable=False
        ),
        sa.Column(
            'type',
            # use the existing ENUM, do not auto-create
            postgresql.ENUM(
                name=enums['notification_type']['name'],
                create_type=False
            ),
            nullable=False,
            server_default=enums['notification_type']['values'][0]  # 'info'
        ),
        sa.Column(
            'read_status',
            sa.Boolean,
            nullable=False,
            server_default=sa.text('false')
        ),
        sa.Column(
            'link',
            sa.String(length=255),
            nullable=True
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    # Drop notifications table
    op.drop_table('notifications')

    # Drop ENUMs
    for e in enums.values():
        pg_enum = postgresql.ENUM(name=e['name'])
        pg_enum.drop(bind=bind, checkfirst=True)
