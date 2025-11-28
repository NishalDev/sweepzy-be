"""initial

Revision ID: 57f2b5ae5405
Revises: 
Create Date: 2025-05-30 17:10:47.914769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM
from geoalchemy2 import Geometry
# revision identifiers, used by Alembic.
revision: str = '57f2b5ae5405'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop & recreate enums
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("DROP TYPE IF EXISTS userstatus CASCADE;")
    op.execute("CREATE TYPE userstatus AS ENUM ('active', 'inactive', 'blocked', 'unverified');")

    op.execute("DROP TYPE IF EXISTS grouptypeenum CASCADE;")
    op.execute("CREATE TYPE grouptypeenum AS ENUM ('public', 'private');")

    op.execute("DROP TYPE IF EXISTS groupstatusenum CASCADE;")
    op.execute("CREATE TYPE groupstatusenum AS ENUM ('active', 'inactive', 'banned');")

    op.execute("DROP TYPE IF EXISTS groupverificationenum CASCADE;")
    op.execute("CREATE TYPE groupverificationenum AS ENUM ('pending', 'verified', 'rejected');")

    op.execute("DROP TYPE IF EXISTS cleanup_event_status_enum CASCADE;")
    op.execute("CREATE TYPE cleanup_event_status_enum AS ENUM ('upcoming', 'ongoing', 'completed', 'cancelled');")

    op.execute("DROP TYPE IF EXISTS cleanup_event_verification_enum CASCADE;")
    op.execute("CREATE TYPE cleanup_event_verification_enum AS ENUM ('pending', 'verified', 'rejected');")

    op.execute("DROP TYPE IF EXISTS eventjoinrole CASCADE;")
    op.execute("CREATE TYPE eventjoinrole AS ENUM ('participant', 'organizer', 'volunteer', 'sponsor');")

    op.execute("DROP TYPE IF EXISTS eventjoinstatus CASCADE;")
    op.execute("CREATE TYPE eventjoinstatus AS ENUM ('pending', 'approved', 'rejected', 'withdrawn');")

    # users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('first_name', sa.String(255), nullable=False),
        sa.Column('last_name', sa.String(255)),
        sa.Column('user_name', sa.String(255), unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('phone', sa.String(20), unique=True),
        sa.Column('avatar', sa.String(255)),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('referral_code', sa.String(255)),
        sa.Column(
            'status',
            ENUM('active', 'inactive', 'blocked', 'unverified', name='userstatus', create_type=False),
            nullable=False,
            server_default='unverified'
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('updated_by', sa.Integer, sa.ForeignKey('users.id')),
    )

    # user_details table
    op.create_table(
        'user_details',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('address', sa.String(255), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('latitude', sa.Float),
        sa.Column('longitude', sa.Float),
        sa.Column('bio', sa.String(500)),
        sa.Column('preferences', sa.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Integer),
        sa.Column('updated_by', sa.Integer),
    )

    # uploads table
    op.create_table(
        'uploads',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', sa.String),
        sa.Column('file_name', sa.String, nullable=False),
        sa.Column('file_url', sa.String, nullable=False),
        sa.Column('content_type', sa.String),
        sa.Column('size', sa.Integer),
        sa.Column('latitude', sa.Float),
        sa.Column('longitude', sa.Float),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.text('now()')),
    )
    # litter_groups table
    op.create_table(
        'litter_groups',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('created_by', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('group_type', ENUM('public', 'private', name='grouptypeenum', create_type=False), nullable=False, server_default='public'),
        sa.Column('location', sa.String(100)),
        sa.Column('member_count', sa.Integer, server_default='0'),
        sa.Column('report_count', sa.Integer, server_default='0'),
        sa.Column('status', ENUM('active', 'inactive', 'banned', name='groupstatusenum', create_type=False), server_default='active'),
        sa.Column('verification_status', ENUM('pending', 'verified', 'rejected', name='groupverificationenum', create_type=False), server_default='pending'),
        sa.Column('geom', Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True),
        sa.Column('is_locked', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    # litter_reports table
    op.create_table(
        'litter_reports',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('group_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('litter_groups.id'), nullable=True),
        sa.Column('upload_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('uploads.id'), nullable=True),
        sa.Column('latitude', sa.Float, nullable=False),
        sa.Column('longitude', sa.Float, nullable=False),
        sa.Column('detection_results', sa.JSON),
        sa.Column('severity', sa.String),
        sa.Column('status', sa.String, nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('is_detected', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_mapped', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_grouped', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('reward_points', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.Column('geom', Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True),
    )

    # litter_detections table
    op.create_table(
        'litter_detections',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('litter_report_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('litter_reports.id'), nullable=False),
        sa.Column('reviewed_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('detected_objects', sa.JSON),
        sa.Column('bounding_boxes', sa.JSON),
        sa.Column('total_litter_count', sa.Integer),
        sa.Column('severity_level', sa.String),
        sa.Column('detection_source', sa.String),
        sa.Column('detection_confidence', sa.Float),
        sa.Column('review_status', sa.String, nullable=False, server_default='pending'),
        sa.Column('review_notes', sa.String),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
          
    # cleanup_events table
    op.create_table(
        'cleanup_events',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('litter_group_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('litter_groups.id'), nullable=False),
        sa.Column('organized_by', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_name', sa.Text, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('location', sa.Text),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('participant_limit', sa.Integer),
        sa.Column('registered_participants', sa.Integer, nullable=False, server_default='0'),
        sa.Column('funding_required', sa.Numeric(12, 2)),
        sa.Column('funds_raised', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('event_status', ENUM('upcoming', 'ongoing', 'completed', 'cancelled', name='cleanup_event_status_enum', create_type=False), nullable=False, server_default='upcoming'),
        sa.Column('verification_status', ENUM('pending', 'verified', 'rejected', name='cleanup_event_verification_enum', create_type=False), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    # event_join table
    op.create_table(
        'event_join',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('cleanup_event_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('cleanup_events.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', ENUM('participant', 'organizer', 'volunteer', 'sponsor', name='eventjoinrole', create_type=False), nullable=False, server_default='participant'),
        sa.Column('status', ENUM('pending', 'approved', 'rejected', 'withdrawn', name='eventjoinstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True)),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('cleanup_event_id', 'user_id', name='uq_event_user'),
    )

    # image_reviews table
    op.create_table(
        'image_reviews',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('litter_report_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('litter_reports.id'), nullable=False),
        sa.Column('reviewed_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('review_status', sa.String, nullable=False, server_default='pending'),
        sa.Column('review_notes', sa.String),
        sa.Column('is_duplicate', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('reviewed_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )

    # otps table
    op.create_table(
        'otps',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('email', sa.String, index=True, nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('purpose', sa.String(50), nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('used', sa.Boolean, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )
    
def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('otps')
    op.drop_table('image_reviews')
    op.drop_table('event_join')
    op.drop_table('litter_groups')
    op.drop_table('cleanup_events')
    op.drop_table('litter_detections')
    op.drop_table('litter_reports')
    op.drop_table('uploads')
    op.drop_table('user_details')
    op.drop_table('users')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS eventjoinstatus CASCADE;")
    op.execute("DROP TYPE IF EXISTS eventjoinrole CASCADE;")
    op.execute("DROP TYPE IF EXISTS cleanup_event_verification_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS cleanup_event_status_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS groupverificationenum CASCADE;")
    op.execute("DROP TYPE IF EXISTS groupstatusenum CASCADE;")
    op.execute("DROP TYPE IF EXISTS grouptypeenum CASCADE;")
    op.execute("DROP TYPE IF EXISTS userstatus CASCADE;")