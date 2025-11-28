# Controller
from fastapi import HTTPException, status
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from api.cleanup_events.cleanup_events_service import CleanupEventService
from api.cleanup_events.cleanup_events_schema import ( EventStatus, VerificationStatus, CleanupEventCreate,CleanupEventRead, CleanupEventUpdate,  CleanupEventDetail, CleanupEventSummary, ReportWithVerifications)
from api.litter_groups.litter_groups_schema import ClusterSuggestion
from api.cleanup_events.event_join_schema import EventParticipantResponse, EventJoinUpdate
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.user.user_schema import UserResponse
from api.litter_reports.litter_reports_model import LitterReport
from api.attendance.attendance_schema import TokenOut, AttendanceOut
from api.notifications.notifications_service import cleanup_event_completed
from utils.query_params import QueryParams
class CleanupEventController:
    @staticmethod
    def create_event(
        payload: CleanupEventCreate,
        db: Session,
        current_user_id: int
    ) -> CleanupEventRead:
        service = CleanupEventService(db)
        ev = service.create_event(payload, current_user_id)
        return CleanupEventRead.model_validate(ev)

    @staticmethod
    def list_events(
        db: Session,
        params: QueryParams[CleanupEvent],
        group_id: Optional[UUID] = None,
    ) -> List[CleanupEventRead]:
        service = CleanupEventService(db)
        evs = service.list_events(params, group_id)
        return [CleanupEventRead.model_validate(e) for e in evs]

    @staticmethod
    def get_event(
        event_id: UUID,
        db: Session,
        user_id: int,
    ) -> CleanupEventRead:
        service = CleanupEventService(db)
        raw = service.get_event(event_id, user_id=user_id)
        if not raw:
            return None

        return CleanupEventRead.model_validate(raw)

    @staticmethod
    def update_event(
        event_id: UUID,
        payload: CleanupEventUpdate,
        db: Session,
        current_user: dict,
    ) -> CleanupEventRead:
        user_id = current_user["id"]
        roles   = current_user.get("roles", [])
        data    = payload.model_dump(exclude_unset=True)

        evt: CleanupEvent = db.query(CleanupEvent).filter_by(id=event_id).first()
        if not evt:
            raise HTTPException(status_code=404, detail="Event not found")

        # ── 1️⃣ verification_status transitions ───────────────────────────────────
        if "verification_status" in data:
            new_vs = data["verification_status"]

        # ── 2️⃣ event_status transitions (guard if you need) ─────────────────────
        if "event_status" in data:
            new_es = data["event_status"]
            if new_es == EventStatus.completed:
                if evt.event_status != EventStatus.ongoing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot complete event: current status is {evt.event_status}"
                    )

        # ── 3️⃣ perform the update ────────────────────────────────────────────────
        service = CleanupEventService(db)
        updated: CleanupEvent = service.update_event(event_id, payload, user_id)

        # ── 4️⃣ fire completed signal if we just moved into 'completed' ─────────────
        if getattr(updated, "event_status", None) == EventStatus.completed:
            cleanup_event_completed.send(
                sender=CleanupEventController,
                event=updated
            )

        # ── 5️⃣ return the API schema ─────────────────────────────────────────────
        return CleanupEventRead.model_validate(updated)
    
    @staticmethod
    def delete_event(
        event_id: UUID,
        db: Session
    ) -> None:
        service = CleanupEventService(db)
        ok = service.delete_event(event_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Event not found")

    @staticmethod
    def register(
        event_id: UUID,
        db: Session,
        current_user_id: int
    ) -> dict:
        """
        Returns a dict with:
          - event: CleanupEventRead
          - token:      TokenOut
        """
        service = CleanupEventService(db)
        rv = service.register_participant(event_id, current_user_id)
        if not rv:
            raise HTTPException(
                status_code=400,
                detail="Unable to register (event full or not found)"
            )
        event, token_str = rv

        # wrap schemas
        event_out = CleanupEventRead.model_validate(event)
        token_out = TokenOut.model_validate({
            "token": token_str,
            "not_valid_before": event.start_date,
            "expires_at":      event.end_date,
        })

        return {"event": event_out, "token": token_out}
    
    @staticmethod
    def list_available_groups(
        db: Session, min_reports: int = 1
    ) -> List[ClusterSuggestion]:
        svc = CleanupEventService(db)
        return svc.list_available_groups(min_reports=min_reports)
    
    @staticmethod
    def list_participants(event_id: UUID, db: Session) -> List[EventParticipantResponse]:
        service = CleanupEventService(db)
        participants = service.list_participants(event_id)

        return [
            EventParticipantResponse(
            user_id=p["user_id"],
            username=p["username"],
            role=p["role"],
            status=p["status"],
            checked_in=p["checked_in"],
        )
        for p in participants
    ]
        
    @staticmethod
    def update_participant(
        event_id: UUID,
        participant_id: int,
        data: EventJoinUpdate,
        db: Session,
        current_user: dict
        ):
        service = CleanupEventService(db)
        result = service.update_participant(event_id, participant_id, data, approver_id=current_user["id"])
        if not result:
            raise HTTPException(status_code=404, detail="Participant not found for this event")
        return result
    
    @staticmethod
    def list_join_roles(db: Session) -> List[str]:
        svc = CleanupEventService(db)
        return svc.list_join_roles()
    
    @staticmethod
    def list_user_joins(
        db: Session,
        current_user: dict
    ) -> List[CleanupEventRead]:
        service = CleanupEventService(db)
        joined_events = service.list_user_joins(current_user["id"])
        return [CleanupEventRead.model_validate(ev) for ev in joined_events]

    @staticmethod
    def list_submitted_events(
        db: Session,
        params: QueryParams[CleanupEvent],
    ) -> List[CleanupEventSummary]:
        svc = CleanupEventService(db)
        evs = svc.list_submitted_events(
            params=params,
        )
        return [CleanupEventSummary.model_validate(e) for e in evs]

    @staticmethod
    def get_submitted_event_details(
    event_id: UUID,
    db: Session
    ) -> CleanupEventDetail:
        svc = CleanupEventService(db)
        ev = svc.get_submitted_event_details(event_id)

        if not ev:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submitted event not found"
        )

        reports = []
        for report in ev.litter_group.litter_reports:
            report_id = report.id
            upload_url = report.upload.file_url if report.upload else None
            verif_data = ev._verifications.get(str(report_id), {"before": [], "after": []})
            reports.append(
                ReportWithVerifications(
                report_id=report_id,
                original_image=upload_url,
                before_photos=verif_data["before"],
                after_photos=verif_data["after"]
            )
        )

        attendance = [AttendanceOut.model_validate(rec) for rec in ev._attendance]

        return CleanupEventDetail(
        id=ev.id,
        event_name=ev.event_name,
        description=ev.description,
        scheduled_date=ev.scheduled_date,
        location=ev.location,
        organized_by=ev.organized_by,
        event_status=ev.event_status,
        verification_status=ev.verification_status,
        reports=reports,
        attendance=attendance
    )