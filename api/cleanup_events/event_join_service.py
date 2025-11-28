from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from api.user.user_model import User as UserModel
from api.cleanup_events.event_join_schema import EventJoinCreate, EventJoinUpdate, EventJoin
from api.cleanup_events.event_join_model import EventJoin as EventJoinModel
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.attendance.attendance_service import AttendanceService
class EventJoinService:
    def __init__(self, db: Session):
        self.db = db
    def create_join(self, data: EventJoinCreate, user_id: int) -> EventJoinModel:
    # Check if already joined
        exists = (
        self.db
        .query(EventJoinModel)
        .filter_by(cleanup_event_id=data.cleanup_event_id, user_id=user_id)
        .first()
    )
        if exists:
            raise HTTPException(status_code=400, detail="Already registered")

    # Fetch the event to inspect its needs_approval flag and organizer
        event = (
        self.db
        .query(CleanupEvent)
        .filter_by(id=data.cleanup_event_id)
        .first()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Cleanup event not found")

        # Capacity check
        if event.participant_limit and event.registered_participants >= event.participant_limit:
            raise HTTPException(status_code=400, detail="Event is full")

        # Determine join status & auto_approved based on event.needs_approval
        if event.needs_approval:
            join_status = 'pending'
            auto_approved = False
        else:
            join_status = 'approved'
            auto_approved = True

        # Decide role: organizer if the creator is the organizer, else volunteer
        role = 'organizer' if event.organized_by == user_id else 'volunteer'

        # Create new join record
        join = EventJoinModel(
            cleanup_event_id=data.cleanup_event_id,
            user_id=user_id,
            status=join_status,
            role=role,
            auto_approved=auto_approved,
        )
        self.db.add(join)

        # Update event participant count
        event.registered_participants += 1

        self.db.commit()
        self.db.refresh(join)

    # Generate attendance token
        AttendanceService(self.db).generate_token(
            event_id=data.cleanup_event_id,
            user_id=user_id,
            length=4  # 4-digit token
        )

        return join

    def list_joins(self, event_id: Optional[UUID] = None, user_id: Optional[int] = None):
        query = self.db.query(EventJoinModel)
        if event_id:
            query = query.filter_by(cleanup_event_id=event_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()

    def get_join(self, join_id: int) -> Optional[EventJoinModel]:
        join = self.db.query(EventJoinModel).get(join_id)
        if not join:
            raise HTTPException(status_code=404, detail="Event‐join record not found")
        return join

    def update_join(self, join_id: int, data: EventJoinUpdate, current_user_id: int) -> Optional[EventJoinModel]:
        join = self.get_join(join_id)
        if not join:
            raise HTTPException(404, "Not found")
        data_dict = data.dict(exclude_unset=True)
        if "status" in data_dict:
            new_status = data_dict["status"]
            if new_status == "approved":
                join.approved_by = current_user_id
                join.approved_at = datetime.utcnow()
            elif new_status == "withdrawn":
                join.withdrawn_at = datetime.utcnow()
        for field, value in data_dict.items():  # Use data_dict instead of data.dict
            setattr(join, field, value)
        self.db.commit()
        self.db.refresh(join)
        return join

    def delete_join(self, join_id: int) -> bool:
        join = self.get_join(join_id)
        if not join:
            return False
        self.db.delete(join)
        self.db.commit()
        return True
    
    def get_participant_by_role(
        self,
        event_id: UUID,
        role: str
    ) -> str:
        """
        Fetch the username of the participant in `event_id` with the given `role`.
        Raises 404 if not found.
        """
        # 1) join EventJoin → UserModel
        join_and_user = (
            self.db
            .query(EventJoinModel, UserModel)
            .join(UserModel, UserModel.id == EventJoinModel.user_id)
            .filter(
                EventJoinModel.cleanup_event_id == event_id,
                EventJoinModel.role == role
            )
            .first()
        )

        if not join_and_user:
            raise HTTPException(status_code=404, detail=f"No participant with role '{role}'")

        event_join, user = join_and_user
        return user.username  # or `.full_name`, etc.