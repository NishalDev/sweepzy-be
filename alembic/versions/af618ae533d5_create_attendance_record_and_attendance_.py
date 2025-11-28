from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'af618ae533d5'
down_revision = 'f771ec85e613'
branch_labels = None
depends_on = None

# Create ENUM type object outside
attendancemethod_enum = postgresql.ENUM(
    'token', 'qr', 'gps', 'otp',
    name='attendancemethod',
    create_type=False  # Do not auto-create when used in tables
)

def upgrade():
    # Manually create the enum only once
    attendancemethod_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'attendance_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=16), nullable=False, unique=True),
        sa.Column('not_valid_before', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['cleanup_events.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.UniqueConstraint('event_id', 'user_id', name='uq_token_event_user'),
    )

    op.create_table(
        'attendance_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('checked_in_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('recorded_by', sa.Integer(), nullable=False),
        sa.Column('method', attendancemethod_enum, nullable=False),  # Reuse the enum object here
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['cleanup_events.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
        sa.UniqueConstraint('event_id', 'user_id', name='uq_attendance_event_user'),
    )

def downgrade():
    op.drop_table('attendance_records')
    op.drop_table('attendance_tokens')
    attendancemethod_enum.drop(op.get_bind(), checkfirst=True)
