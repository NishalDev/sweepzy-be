# config/points_config.py

from enum import Enum

class PointReason(str, Enum):
    cleanup_completed         = "cleanup_completed"      # +100
    event_hosted              = "event_hosted"           # +50 (only when 5+ signups)
    badge_assigned            = "badge_assigned"         # +5
    first_login               = "first_login"            # +2
    profile_completed         = "profile_completed"      # +3
    uploaded_litter_report    = "uploaded_litter_report" # +10
    event_attended            = "event_attended"         # +50
    hosted_five_events        = "hosted_five_events"     # +150 (one-time milestone)
    consistency_streak        = "consistency_streak"     # +75
    creative_story_featured   = "creative_story_featured" # +30

# Finalized point values
POINT_VALUES = {
    PointReason.cleanup_completed:        100,
    PointReason.event_hosted:              50,  # Only triggered when 5+ signups
    PointReason.event_attended:            50,
    PointReason.uploaded_litter_report:    10,
    PointReason.badge_assigned:             5,
    PointReason.first_login:                2,
    PointReason.profile_completed:          3,
    PointReason.hosted_five_events:       150,
    PointReason.consistency_streak:        75,
    PointReason.creative_story_featured:   30,
}
