from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from api.dashboard.dashboard_service import (
    get_total_litter_reports,
    get_events_attended,
    get_nearby_litter,
    get_upcoming_events,
    get_total_events,
    get_participants_engaged,
    get_verified_cleanups,
    get_analytic_cards,
    get_litter_type_breakdown,
    get_next_upcoming_event,
    get_my_events,
    get_participant_names,
    get_user_points,
    get_registered_events,
    get_pending_approvals
)
from api.dashboard.dashboard_schema import (
    DashboardResponse,
    AnalyticsOut,
    LitterTypeBreakdownOut,
)


def assemble_dashboard(
    db: Session,
    user_id: int,
    user_lat: Optional[float],
    user_lng: Optional[float],
    is_host: bool  # now unused, but left for signature
) -> DashboardResponse:
    # ─── User metrics ──────────────────────────────────────
    total_reports = get_total_litter_reports(db, user_id)
    cleaned = get_events_attended(db, user_id)
    user_points    = get_user_points(db, user_id)       
    nearby = []
    if user_lat is not None and user_lng is not None:
        nearby = get_nearby_litter(db, user_lat, user_lng)
    upcoming = get_upcoming_events(db)
    registered = get_registered_events(db, user_id)

    # ─── Host metrics ──────────────────────────────────────
    total_events = get_total_events(db, user_id)
    participants_count = get_participants_engaged(db, user_id)
    verified_count = get_verified_cleanups(db, user_id)
    analytics_dict = get_analytic_cards(db, user_id)
    breakdown_dict = get_litter_type_breakdown(db)
    next_ev = get_next_upcoming_event(db, user_id)
    my_events = get_my_events(db, user_id)
    pending_approvals = get_pending_approvals(db, user_id)
    participant_names = []
    if next_ev:
        participant_names = get_participant_names(db, next_ev.id)

    return DashboardResponse(
        # user
        total_reports=total_reports,
        cleaned_reports=cleaned,
        points= user_points,
        nearby_litter=nearby,
        upcoming_events=upcoming,
        registered_events=registered,
        # host
        total_events=total_events,
        pending_approvals=pending_approvals,
        participants_engaged=participants_count,
        verified_cleanups=verified_count,
        analytics=AnalyticsOut(**analytics_dict),
        breakdown=LitterTypeBreakdownOut(**breakdown_dict),
        next_event=next_ev,
        my_events=my_events,
        participant_names=participant_names,
    )
