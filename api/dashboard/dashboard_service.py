import math
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import aliased, Session
from sqlalchemy import and_, func, text

from api.litter_reports.litter_reports_model import LitterReport
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.litter_groups.litter_groups_model import LitterGroup
from api.litter_detections.litter_detections_model import LitterDetection
from api.dashboard.dashboard_schema import EventOut
from api.user.user_points_model import UserPointsLog
from api.cleanup_events.event_join_model import EventJoin
# ─── User Dashboard Services ────────────────────────────────────────────────

def get_total_litter_reports(db: Session, user_id: int) -> int:
    return (
        db.query(LitterReport)
          .filter(LitterReport.user_id == user_id)
          .count()
    )


def get_events_attended(db: Session, user_id: int) -> int:
    """
    Returns the total number of events the user has registered for.
    If you only want to count completed events, you can
    join to the Event model and filter on its status.
    """
    return (
        db.query(EventJoin)
          .filter(EventJoin.user_id == user_id)
          .count()
    )


def _haversine_distance(lat1, lon1, lat2, lon2):
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 6371 * c


def get_nearby_litter(db: Session, user_lat: float, user_lng: float, radius_km=5.0):
    reports = db.query(LitterReport).all()
    out = []
    for r in reports:
        if r.latitude is None or r.longitude is None:
            continue
        dist = _haversine_distance(user_lat, user_lng, r.latitude, r.longitude)
        if dist <= radius_km:
            before = getattr(r.upload, "file_url", None)
            after = before if r.status == "resolved" else None
            out.append({
                "id": r.id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "before_image_url": before,
                "after_image_url": after,
                "distance_km": round(dist, 2),
                "status": r.status,
            })
    out.sort(key=lambda x: x["distance_km"])
    return out

def get_registered_events(db: Session, user_id: int) -> List[EventOut]:
    """
    Returns all events that the given user has joined/registered for,
    including centroid coordinates and event_status.
    """
    Group = aliased(LitterGroup)

    rows = (
        db.query(
            CleanupEvent,
            func.ST_Y(Group.geom).label("centroid_lat"),
            func.ST_X(Group.geom).label("centroid_lng"),
        )
        .join(EventJoin, EventJoin.cleanup_event_id == CleanupEvent.id)
        .outerjoin(Group, CleanupEvent.litter_group_id == Group.id)
        .filter(EventJoin.user_id == user_id)
        .order_by(CleanupEvent.scheduled_date.desc())
        .all()
    )

    return [
        EventOut(
            id             = event.id,
            name           = event.event_name,
            date           = event.scheduled_date,
            location       = event.location,
            centroid_lat   = float(lat) if lat is not None else None,
            centroid_lng   = float(lng) if lng is not None else None,
            event_status   = event.event_status,
        )
        for event, lat, lng in rows
    ]
    
def get_upcoming_events(db: Session) -> List[EventOut]:
    Group = aliased(LitterGroup)
    now = datetime.utcnow()

    rows = (
        db.query(
            CleanupEvent,
            func.ST_Y(Group.geom).label("centroid_lat"),
            func.ST_X(Group.geom).label("centroid_lng"),
        )
        .outerjoin(Group, CleanupEvent.litter_group_id == Group.id)
        .filter(
            
            CleanupEvent.event_status == "upcoming",
        )
        .order_by(CleanupEvent.scheduled_date.asc())
        .all()
    )

    out: List[EventOut] = []
    for event, lat, lng in rows:
        out.append(
            EventOut(
                id             = event.id,
                name           = event.event_name,
                date           = event.scheduled_date,
                location       = event.location,
                centroid_lat   = float(lat) if lat is not None else None,
                centroid_lng   = float(lng) if lng is not None else None,
                event_status   = "upcoming",
            )
        )
    return out

# ─── Host Dashboard Services ────────────────────────────────────────────────

def get_total_events(db: Session, host_id: int) -> int:
    return db.query(CleanupEvent).filter(CleanupEvent.organized_by == host_id).count()


def get_participants_engaged(db: Session, host_id: int) -> int:
    total = (
        db.query(func.coalesce(func.sum(CleanupEvent.registered_participants), 0))
        .filter(CleanupEvent.organized_by == host_id)
        .scalar()
    )
    return int(total)


def get_verified_cleanups(db: Session, host_id: int) -> int:
    return (
        db.query(CleanupEvent)
        .filter(
            CleanupEvent.organized_by == host_id,
            CleanupEvent.verification_status == "verified",
        )
        .count()
    )


def get_analytic_cards(db: Session, host_id: int) -> Dict[str, Any]:
    total = get_total_events(db, host_id)
    engaged = get_participants_engaged(db, host_id)
    verified = get_verified_cleanups(db, host_id)
    avg = round(engaged / total, 2) if total else 0.0
    pct = round((verified / total) * 100, 2) if total else 0.0
    return {
        "avg_participants_per_event": avg,
        "percent_events_verified": pct,
    }


def get_litter_type_breakdown(db: Session) -> Dict[str, int]:
    sql = text("""
      SELECT elem->>'label' AS label, count(*) AS cnt
      FROM litter_detections ld,
           jsonb_array_elements(ld.detected_objects::jsonb) elem
      GROUP BY label
    """)
    rows = db.execute(sql).fetchall()
    keys = ["plastic_bottle", "plastic_bag", "paper_waste", "food_wrapper"]
    result = {k: 0 for k in keys}
    for label, cnt in rows:
        if label in result:
            result[label] = cnt
    return result


def get_next_upcoming_event(db: Session, host_id: int) -> Optional[EventOut]:
    now = datetime.utcnow()
    Group = aliased(LitterGroup)
    row = (
        db.query(
            CleanupEvent,
            func.ST_Y(Group.geom).label("centroid_lat"),
            func.ST_X(Group.geom).label("centroid_lng"),
        )
        .outerjoin(Group, CleanupEvent.litter_group_id == Group.id)
        .filter(
            CleanupEvent.organized_by == host_id,
            CleanupEvent.scheduled_date >= now,
        )
        .order_by(CleanupEvent.scheduled_date.asc())
        .first()
    )
    if not row:
        return None

    event, lat, lng = row
    return EventOut(
        id=event.id,
        name=event.event_name,
        date=event.scheduled_date,
        location=event.location,
        centroid_lat=float(lat) if lat else None,
        centroid_lng=float(lng) if lng else None,
    )


def get_my_events(db: Session, host_id: int) -> List[EventOut]:
    now = datetime.utcnow()
    Group = aliased(LitterGroup)
    rows = (
        db.query(
            CleanupEvent,
            func.ST_Y(Group.geom).label("centroid_lat"),
            func.ST_X(Group.geom).label("centroid_lng"),
        )
        .outerjoin(Group, CleanupEvent.litter_group_id == Group.id)
        .filter(CleanupEvent.organized_by == host_id)
        .order_by(CleanupEvent.scheduled_date.desc())
        .all()
    )
    out: List[EventOut] = []
    for event, lat, lng in rows:
        out.append(
            EventOut(
                id=event.id,
                name=event.event_name,
                date=event.scheduled_date,
                location=event.location,
                centroid_lat=float(lat) if lat else None,
                centroid_lng=float(lng) if lng else None,
                event_status=event.event_status if event.event_status else None,
            )
        )
    return out


def get_participant_names(db: Session, event_id: int) -> List[str]:
    # join users via EventJoin for that event
    from api.cleanup_events.event_join_model import EventJoin
    from api.user.user_model import User
    rows = (
        db.query(User.username)
        .join(EventJoin, EventJoin.user_id == User.id)
        .filter(EventJoin.cleanup_event_id == event_id)
        .all()
    )
    return [r[0] for r in rows]


#get points

def get_user_points(db: Session, user_id: int) -> int:
    """
    Fetch the total points for `user_id` by summing the `delta` column
    in user_points_log. Defaults to 0 if no entries exist.
    """
    total_points = (
        db.query(func.coalesce(func.sum(UserPointsLog.delta), 0))
          .filter(UserPointsLog.user_id == user_id)
          .scalar()
    )
    return int(total_points)

def get_pending_approvals(db: Session, user_id: int) -> List[LitterReport]:
    """
    Fetch all litter reports that are pending approval for the given user.
    """
    return (
        db.query(CleanupEvent)
          .filter(
              CleanupEvent.organized_by == user_id,
              CleanupEvent.verification_status == "submitted"
          )
          .count()
    )
