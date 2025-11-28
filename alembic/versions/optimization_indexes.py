"""Add performance indexes

Revision ID: optimization_indexes
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'optimization_indexes'
down_revision = None  # Update this to your latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance-critical indexes"""
    
    # User table indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email 
        ON users(email);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_status 
        ON users(status);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_is_verified 
        ON users(is_verified);
    """)
    
    # Litter reports indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_litter_reports_status 
        ON litter_reports(status);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_litter_reports_user_id 
        ON litter_reports(user_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_litter_reports_group_id 
        ON litter_reports(group_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_litter_reports_created_at 
        ON litter_reports(created_at DESC);
    """)
    
    # Cleanup events indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cleanup_events_status 
        ON cleanup_events(verification_status);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cleanup_events_organizer_id 
        ON cleanup_events(organizer_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cleanup_events_scheduled_date 
        ON cleanup_events(scheduled_date DESC);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cleanup_events_litter_group_id 
        ON cleanup_events(litter_group_id);
    """)
    
    # Event joins indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_joins_cleanup_event_id 
        ON event_joins(cleanup_event_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_joins_user_id 
        ON event_joins(user_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_joins_status 
        ON event_joins(status);
    """)
    
    # Composite indexes for common query patterns
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_joins_event_user 
        ON event_joins(cleanup_event_id, user_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_litter_reports_user_status 
        ON litter_reports(user_id, status);
    """)
    
    # User roles indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_roles_user_id 
        ON user_roles(user_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_roles_role_id 
        ON user_roles(role_id);
    """)
    
    # Role permissions indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_role_permissions_role_id 
        ON role_permissions(role_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_role_permissions_permission_id 
        ON role_permissions(permission_id);
    """)
    
    # OTP table indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_otp_email_purpose 
        ON otp(email, purpose);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_otp_expires_at 
        ON otp(expires_at);
    """)
    
    # Uploads indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uploads_user_id 
        ON uploads(user_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uploads_created_at 
        ON uploads(created_at DESC);
    """)
    
    # Litter detections indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_litter_detections_report_id 
        ON litter_detections(litter_report_id);
    """)
    
    # Photo verifications indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_photo_verifications_event_id 
        ON photo_verifications(event_id);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_photo_verifications_status 
        ON photo_verifications(status);
    """)
    
    # JSON indexes for PostgreSQL (if using JSONB)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_litter_reports_detection_status 
        ON litter_reports USING GIN ((detection_results->>'status'))
        WHERE detection_results IS NOT NULL;
    """)
    
    # Partial indexes for common filters
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active 
        ON users(id) WHERE status = 'active';
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_verified 
        ON users(id) WHERE is_verified = true;
    """)


def downgrade() -> None:
    """Remove performance indexes"""
    
    # Drop all the indexes we created
    indexes_to_drop = [
        'idx_users_email',
        'idx_users_status',
        'idx_users_is_verified',
        'idx_litter_reports_status',
        'idx_litter_reports_user_id',
        'idx_litter_reports_group_id',
        'idx_litter_reports_created_at',
        'idx_cleanup_events_status',
        'idx_cleanup_events_organizer_id',
        'idx_cleanup_events_scheduled_date',
        'idx_cleanup_events_litter_group_id',
        'idx_event_joins_cleanup_event_id',
        'idx_event_joins_user_id',
        'idx_event_joins_status',
        'idx_event_joins_event_user',
        'idx_litter_reports_user_status',
        'idx_user_roles_user_id',
        'idx_user_roles_role_id',
        'idx_role_permissions_role_id',
        'idx_role_permissions_permission_id',
        'idx_otp_email_purpose',
        'idx_otp_expires_at',
        'idx_uploads_user_id',
        'idx_uploads_created_at',
        'idx_litter_detections_report_id',
        'idx_photo_verifications_event_id',
        'idx_photo_verifications_status',
        'idx_litter_reports_detection_status',
        'idx_users_active',
        'idx_users_verified'
    ]
    
    for index_name in indexes_to_drop:
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name};")