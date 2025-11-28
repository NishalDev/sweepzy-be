from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session,aliased, joinedload, selectinload
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql import text, exists, insert, update
from shapely.geometry import mapping
from shapely.wkb import loads as to_shape
from fastapi import HTTPException
from datetime import datetime

from api.litter_reports.cleanup_event_reports_model import CleanupEventReport
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.cleanup_events.cleanup_events_schema import (
    CleanupEventCreate,
    CleanupEventUpdate,
    CleanupEventRead,
    EventStatus,
    VerificationStatus
)
from api.cleanup_events.event_join_schema import EventJoinUpdate
from api.cleanup_events.event_join_model import EventJoin, EventJoinRole, EventJoinStatus
from api.litter_reports.litter_reports_model import LitterReport
from api.litter_groups.litter_groups_model import LitterGroup
from api.litter_groups.litter_groups_schema import ClusterSuggestion
from api.litter_reports.litter_reports_schema import LitterReportResponse
from api.user.user_model import User
from api.user.user_service import award_points
from api.attendance.attendance_service import AttendanceService
from api.attendance.attendance_records_model import AttendanceRecord
from api.photo_verifications.photo_verifications_model import PhotoVerification
from api.badges.badges_service import BadgeService
from config.points_config import PointReason
from config.badges_config import BadgeKey
from utils.query_params import QueryParams
class CleanupEventService:
    def __init__(self, db: Session):
        self.db = db

    def create_event(self, data: CleanupEventCreate, organizer_id: int) -> CleanupEvent:
        """
        data may contain either:
        - data.litter_group_id: UUID of an existing group to lock & use, OR
        - data.litter_report_ids: List[UUID] of reports to bundle into a new group.
        """

        group = None

        # ─── 1️⃣ Handle incoming report list ──────────────────────────────────────────
        if getattr(data, "litter_report_ids", None):
            # Create a new group to hold those reports
            group = LitterGroup(
                name=f"{data.event_name} - auto-group",
                description=data.description or "",
                created_by=organizer_id,
                status="locked",            # immediately locked
                is_locked=True,
            )
            self.db.add(group)
            self.db.flush()
            reports = (
                self.db.query(LitterReport)
                .filter(LitterReport.id.in_(data.litter_report_ids))
                .all()
            )
            print(f"[DEBUG] Fetched {len(reports)} reports to assign")
            if len(reports) != len(data.litter_report_ids):
                raise HTTPException(404, "One or more reports not found")

            for rpt in reports:
                rpt.group_id = group.id
                rpt.is_grouped = True
                print(f"[DEBUG] Assigned report {rpt.id} to group {group.id}")
        # ─── 2️⃣ Or lock an existing group ───────────────────────────────────────────
        elif data.litter_group_id:
            group = (
                self.db.query(LitterGroup)
                .filter(LitterGroup.id == data.litter_group_id)
                .first()
            )
            if not group:
                raise HTTPException(404, "Group not found")
            if group.is_locked:
                raise HTTPException(409, "Cannot create event: group is already locked.")
            # lock it
            group.is_locked = True

        # ─── 3️⃣ Create the CleanupEvent ─────────────────────────────────────────────
        event = CleanupEvent(
            litter_group_id = group.id if group else None,
            organized_by     = organizer_id,
            event_name       = data.event_name,
            description      = data.description,
            location         = data.location,
            scheduled_date   = data.scheduled_date,
            participant_limit= data.participant_limit,
            funding_required = data.funding_required,
            needs_approval   = data.needs_approval,
        )
        self.db.add(event)
        self.db.flush()  # populates event.id

        # tie the group back to this event
        if group:
            group.event_id = event.id

        # ─── 4️⃣ Map reports into the event ─────────────────────────────────────────
        # Any report with group_id == group.id gets associated
        if group:
            reports = (
                self.db.query(LitterReport)
                .filter(LitterReport.group_id == group.id)
                .all()
            )
            for report in reports:
                assoc = CleanupEventReport(
                    event_id  = event.id,
                    report_id = report.id,
                )
                self.db.add(assoc)
                event.event_associations.append(assoc)
                report.event_id = event.id  # optional on the LitterReport side

        # ─── 5️⃣ Commit & refresh ────────────────────────────────────────────────────
        self.db.commit()
        self.db.refresh(event)

        # # ─── 6️⃣ Award points & badges ───────────────────────────────────────────────
        # award_points(
        #     db=self.db,
        #     current_user={"id": organizer_id},
        #     user_id=organizer_id,
        #     reason=PointReason.event_hosted
        # )
        # BadgeService.assign_badge_to_user(
        #     db=self.db,
        #     user_id=organizer_id,
        #     badge_id=BadgeKey.EVENT_HOST
        # )

        return event


    def list_events(
    self,
    params: QueryParams[CleanupEvent],         # pagination & sort params
    group_id: Optional[UUID] = None,
    ) -> List[CleanupEvent]:
        # alias the group table so we can pull in its fields
        Group = aliased(LitterGroup)

        # 1️⃣ build the base query joining in group & organizer
        q = (
            self.db.query(
                CleanupEvent,
                Group.severity.label("group_severity"),
                func.ST_Y(Group.geom).label("centroid_lat"),
                func.ST_X(Group.geom).label("centroid_lng"),
                User.username.label("organizer_name"),
            )
            .outerjoin(Group, CleanupEvent.litter_group_id == Group.id)
            .outerjoin(User, CleanupEvent.organized_by == User.id)
        )

        # 2️⃣ apply group filter if provided
        if group_id:
            q = q.filter(CleanupEvent.litter_group_id == group_id)

        # 3️⃣ apply sort & pagination from params
        try:
            q = params.apply(q, CleanupEvent)
        except ValueError as e:
            # you can turn this into an HTTP 400 if you're in a controller/router
            raise

        # 4️⃣ fetch & peel out the raw rows into your CleanupEvent instances
        rows = q.all()
        results: List[CleanupEvent] = []
        for event, grp_sev, lat, lng, org_name in rows:
            setattr(event, "severity",        grp_sev)
            setattr(event, "organizer_name",  org_name)
            setattr(event, "centroid_lat",    float(lat) if lat is not None else None)
            setattr(event, "centroid_lng",    float(lng) if lng is not None else None)
            results.append(event)

        return results

    
    def get_event(self, event_id: UUID, user_id: int) -> Optional[CleanupEvent]:
        try:
            Group = aliased(LitterGroup)

            # 1️⃣ Query: Event → Group → Reports → Upload (join everything)
            row = (
                self.db.query(
                    CleanupEvent,
                    Group,
                    func.ST_Y(Group.geom).label("centroid_lat"),
                    func.ST_X(Group.geom).label("centroid_lng"),
                )
                .outerjoin(Group, CleanupEvent.litter_group_id == Group.id)
                .options(
                    joinedload(CleanupEvent.litter_group)
                        .joinedload(LitterGroup.litter_reports)
                        .joinedload(LitterReport.upload),
                    selectinload(CleanupEvent.litter_reports)  # reports from mapping table
                        .joinedload(LitterReport.upload),
                )
                .filter(CleanupEvent.id == event_id)
                .one()
            )

            event, group, lat, lng = row

            # 2️⃣ Set severity from group
            event.severity = group.severity if group else None

            # 3️⃣ Gather reports: from group + from mapping table (merge)
            report_map = {str(r.id): r for r in event.litter_reports}

            if group:
                for r in group.litter_reports:
                    if str(r.id) not in report_map:
                        report_map[str(r.id)] = r

            # 4️⃣ Serialize reports with image_url and detection_id
            event.reports = []
            for r in report_map.values():
                base = r.__dict__.copy()
                base.pop("geom", None)

                event.reports.append(
                    LitterReportResponse(
                        **base,
                        geom=r.geom,
                        image_url=getattr(r.upload, "file_url", None),
                        detection_id=r.detections[0].id if getattr(r, "detections", []) else None,
                    )
                )

            # 5️⃣ Organizer name
            organizer = self.db.query(User).filter(User.id == event.organized_by).first()
            event.organizer_name = organizer.username if organizer else None

            # 6️⃣ Centroid
            event.centroid_lat = float(lat) if lat is not None else None
            event.centroid_lng = float(lng) if lng is not None else None

            # 7️⃣ Join status
            join = (
                self.db.query(EventJoin)
                .filter(
                    EventJoin.cleanup_event_id == event_id,
                    EventJoin.user_id == user_id,
                )
                .first()
            )
            event.joined = bool(join)
            event.user_role = join.role if join else None
            event.approval_status = join.status if join else None

            return event

        except NoResultFound:
            return None

    def update_event(
        self,
        event_id: UUID,
        data: CleanupEventUpdate,
        user_id: int
    ) -> Optional[CleanupEvent]:
    # 1️⃣ Fetch the event
        event = (
            self.db.query(CleanupEvent)
               .filter(CleanupEvent.id == event_id)
               .first()
        )
        if not event:
            return None

    # 2️⃣ Snapshot old statuses and prepare update payload
        old_event_status        = event.event_status
        old_verification_status = event.verification_status
        update_data = data.model_dump(exclude_unset=True)

    # 3️⃣ Apply all updates
        for field, value in update_data.items():
            setattr(event, field, value)

    # 4️⃣ Commit & refresh
        self.db.commit()
        self.db.refresh(event)

    # 5️⃣ Determine which trigger(s) fired
        just_completed = (
            "event_status" in update_data
            and event.event_status == EventStatus.completed.value
            and old_event_status != EventStatus.completed.value
        )
        verif_changed = (
            "verification_status" in update_data
            and event.verification_status != old_verification_status
        )

        # 6️⃣ Only proceed if the event is now completed
        if event.event_status == EventStatus.completed.value and (just_completed or verif_changed):
        # ————————————————————————————————————————————————————————————
        # A) VERIFIED ➔ award cleanup_completed to organizer + attendees
            if event.verification_status == VerificationStatus.verified.value:
            # Organizer reward
                award_points(
                db=self.db,
                current_user={"id": event.organized_by},
                user_id=event.organized_by,
                reason=PointReason.cleanup_completed
                )
                BadgeService.assign_badge_to_user(
                db=self.db,
                user_id=event.organized_by,
                badge_id=BadgeKey.EVENT_COMPLETED
                )

            # Each approved attendee
                attendees = (
                    self.db.query(EventJoin)
                   .filter(
                       EventJoin.cleanup_event_id == event_id,
                       EventJoin.status            == EventJoinStatus.approved
                   )
                   .all()
                )
                for join in attendees:
                    if join.user_id == event.organized_by:
                        continue
                    award_points(
                        db=self.db,
                        current_user={"id": event.organized_by},
                        user_id=join.user_id,
                        reason=PointReason.event_attended
                    )
                    BadgeService.assign_badge_to_user(
                        db=self.db,
                        user_id=join.user_id,
                        badge_id=BadgeKey.EVENT_ATTENDED
                    )

        # ————————————————————————————————————————————————————————————
        # B) REJECTED ➔ award only event_attended to attendees
            elif event.verification_status == VerificationStatus.rejected.value:
                attendees = (
                    self.db.query(EventJoin)
                    .filter(
                        EventJoin.cleanup_event_id == event_id,
                        EventJoin.status            == EventJoinStatus.approved
                    )
                    .all()
                )
                for join in attendees:
                    if join.user_id == event.organized_by:
                        continue
                    award_points(
                        db=self.db,
                        current_user={"id": event.organized_by},
                        user_id=join.user_id,
                        reason=PointReason.event_attended
                    )
                    BadgeService.assign_badge_to_user(
                        db=self.db,
                        user_id=join.user_id,
                        badge_id=BadgeKey.EVENT_ATTENDED
                    )   

            return event

    def delete_event(self, event_id: UUID) -> bool:
        event = self.get_event(event_id)
        if not event:
            return False
        self.db.delete(event)
        self.db.commit()
        return True

    def register_participant(
        self,
        event_id: UUID,
        user_id: int
    ) -> Optional[Tuple[CleanupEvent, str]]:
        """
        - Increments registered_participants
        - Generates an attendance token
        - Returns (event, token) or None if full/not found
        """
        # 1) load event
        event = self.db.query(CleanupEvent).get(event_id)
        if not event:
            return None

        # 2) check capacity
        if event.participant_limit and event.registered_participants >= event.participant_limit:
            return None

        # 3) increment
        event.registered_participants += 1
        self.db.commit()
        self.db.refresh(event)

        # 4) generate attendance token
        token = AttendanceService(self.db).generate_token(
            event_id=event_id,
            user_id=user_id,
            length=4
        ).token

        return event, token
    
    def list_available_groups(
        self,
        min_reports: int = 1
    ) -> List[ClusterSuggestion]:
        """
        Return all stored litter groups that have at least `min_reports` reports,
        along with their persisted centroid as GeoJSON for UI selection.
        """
        groups = (
            self.db
            .query(LitterGroup)
            .filter(LitterGroup.report_count >= min_reports)
            .all()
        )

        out: List[ClusterSuggestion] = []
        for grp in groups:
            centroid_geojson: Optional[Dict[str, Any]] = None
            if grp.geom is not None:
                try:
                    geom_shape = to_shape(grp.geom)
                    centroid_geojson = mapping(geom_shape)
                except Exception:
                    centroid_geojson = None

            # Remove the int check to allow any id type (UUID, int, etc.)
            out.append(ClusterSuggestion(
                cluster_id=str(grp.id),  # Use string to avoid Pydantic int error, or adjust your schema to accept str/UUID
                report_count=grp.report_count,
                centroid=centroid_geojson or {},
                bbox={},                 # Placeholder; no stored bbox
            ))

        return out
    
    def list_participants(self, event_id: UUID) -> List[dict]:
        """
        Returns all the participants (username, role, checked_in) of this event.
        """
        # Get all attendance records for this event
        checked_in_users = set(
        r[0]
        for r in self.db.query(AttendanceRecord.user_id)
        .filter(AttendanceRecord.event_id == event_id)
        .all()
        )

    # Fetch users and join info
        results = (
        self.db.query(User, EventJoin)
        .join(EventJoin, EventJoin.user_id == User.id)
        .filter(EventJoin.cleanup_event_id == event_id)
        .all()
        )

        response = []
        for user, join in results:
            response.append({
            "user_id": user.id,
            "username": user.username,
            "role": join.role,
            "status": join.status,
            "checked_in": user.id in checked_in_users,
        })

        return response
    
    def update_participant(
        self,
        event_id: UUID,
        user_id: int,
        data: EventJoinUpdate,
        approver_id: int
    ) -> Optional[EventJoin]:
        ej = (
        self.db.query(EventJoin)
        .filter(EventJoin.cleanup_event_id == event_id, EventJoin.user_id == user_id)
        .first()
        )
        if not ej:
            return None

        if data.status is not None:
            ej.status = data.status
            if data.status == EventJoinStatus.approved:
                ej.approved_by = approver_id
                ej.approved_at = datetime.utcnow()

        if data.role is not None:
            ej.role = data.role

        self.db.commit()
        self.db.refresh(ej)
        return ej
    
    def list_join_roles(self) -> List[str]:
        """
        Return all possible EventJoinRole values, excluding 'organizer'.
        """
        return [
            role.value
            for role in EventJoinRole
            if role is not EventJoinRole.organizer
        ]
        
    def list_user_joins(self, user_id: int) -> List[CleanupEvent]:
        """
        Fetch all cleanup events that the given user has joined.
        """
        return (
            self.db.query(CleanupEvent)
                .join(EventJoin, EventJoin.cleanup_event_id == CleanupEvent.id)
                .filter(EventJoin.user_id == user_id)
                .all()
        )
        
    def list_submitted_events(
        self,
        params: QueryParams[CleanupEvent],  # <-- fixed generic
    ) -> List[CleanupEvent]:
        """
        Returns all events whose verification_status is 'submitted',
        sorted & paginated according to params.
        """
        # 1. Base filter
        query = (
            self.db
                .query(CleanupEvent)
                .filter(CleanupEvent.verification_status == "submitted")
        )

        # 2. Sorting: use params if valid, otherwise scheduled_date desc
        sort_col = getattr(CleanupEvent, params.sort_by, None)
        if sort_col:
            query = query.order_by(
                desc(sort_col) if params.sort_order == "desc" else asc(sort_col)
            )
        else:
            query = query.order_by(CleanupEvent.scheduled_date.desc())

        # 3. Pagination
        return query.offset(params.offset).limit(params.limit).all()

    def get_submitted_event_details(
    self, event_id: UUID
    ) -> Optional[CleanupEvent]:
        """
        Load one submitted event, its original reports,
        any BEFORE/AFTER verifications, and attendance.
        """
        ev = (
            self.db
            .query(CleanupEvent)
            .options(
                # load the linked group → its reports → each report's upload & detections
                joinedload(CleanupEvent.litter_group)
                .joinedload(LitterGroup.litter_reports)
                .joinedload(LitterReport.upload),
                joinedload(CleanupEvent.litter_group)
                .joinedload(LitterGroup.litter_reports)
                .joinedload(LitterReport.detections),
            )
            .filter(
                CleanupEvent.id == event_id,
                CleanupEvent.verification_status == "submitted"
            )
            .one_or_none()
        )
        if not ev:
            return None

        # preload all BEFORE/AFTER verifications
        verifs = (
            self.db
            .query(PhotoVerification)
            .filter(PhotoVerification.event_id == event_id)
            .all()
        )
        # attach by report_id → phase → urls
        ev._verifications = {}
        for v in verifs:
            rpt = str(v.report_id)
            ev._verifications.setdefault(rpt, {"before": [], "after": []})
            ev._verifications[rpt][v.phase.value] = v.photo_urls

        # load attendance
        ev._attendance = (
            self.db
            .query(AttendanceRecord)
            .filter(AttendanceRecord.event_id == event_id)
            .all()
        )

        return ev