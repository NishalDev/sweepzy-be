"""create roles, user_roles, permissions, role_permissions table

Revision ID: d33b3fc6cd9f
Revises: 3978fc795512
Create Date: 2025-07-04 09:41:35.594578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd33b3fc6cd9f'
down_revision: Union[str, None] = '3978fc795512'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(length=50), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
    )

    # 2) permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
    )

    # 3) role_permissions mapping table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_id', sa.Integer, sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    # 4) user_roles mapping table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
