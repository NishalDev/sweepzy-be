from fastapi import HTTPException
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.cleanup_events.event_join_service import EventJoinService
from api.cleanup_events.event_join_schema import (
    EventJoin as EventJoinSchema,
    EventJoinCreate,
    EventJoinUpdate,
)
from api.notifications.notifications_service import cleanup_event_joined

class EventJoinController:
    @staticmethod
    def create_join(
        payload: EventJoinCreate,
        db: Session,
        current_user_id: int
    ) -> EventJoinSchema:
        # 1) Delegate to the service to insert & commit the join row
        service = EventJoinService(db)
        join = service.create_join(payload, current_user_id)

        # 2) Load the Event so the listener can pick up its name/id
        event = db.get(CleanupEvent, payload.cleanup_event_id)
        if not event:
            raise ValueError(f"Event {payload.cleanup_event_id} not found")

        # 3) Fire the signal right here in the controller
        #    — pass the sender as a positional argument, not via `sender=`
        cleanup_event_joined.send(
            EventJoinController,     # <-- positional sender
            user_id=current_user_id,
            event=event
        )

        # 4) Return the Pydantic-validated response
        return EventJoinSchema.model_validate(join)

    @staticmethod
    def list_joins(
        db: Session,
        cleanup_event_id: Optional[UUID] = None,
        user_id: Optional[int] = None
    ) -> List[EventJoinSchema]:
        service = EventJoinService(db)
        joins = service.list_joins(
            event_id=cleanup_event_id,
            user_id=user_id
        )
        return [EventJoinSchema.model_validate(j) for j in joins]

    @staticmethod
    def get_join(
        join_id: int,
        db: Session
    ) -> EventJoinSchema:
        service = EventJoinService(db)
        join = service.get_join(join_id)
        if not join:
            raise HTTPException(status_code=404, detail="Join not found")
        return EventJoinSchema.model_validate(join)

    @staticmethod
    def update_join(
        join_id: int,
        payload: EventJoinUpdate,
        db: Session,
        current_user_id: int
    ) -> EventJoinSchema:
        service = EventJoinService(db)
        join = service.update_join(join_id, payload, current_user_id)
        if not join:
            raise HTTPException(status_code=404, detail="Join not found")
        return EventJoinSchema.model_validate(join)

    @staticmethod
    def delete_join(
        join_id: int,
        db: Session
    ) -> None:
        service = EventJoinService(db)
        success = service.delete_join(join_id)
        if not success:
            raise HTTPException(status_code=404, detail="Join not found")

    @staticmethod
    def get_participant_by_role(
        event_id: UUID,
        role: str,
        db: Session
    ) -> str:
        """
        Fetches the username of the participant in `event_id` with the given `role`.
        Raises 404 if not found.
        """
        join_service = EventJoinService(db)
        username = join_service.get_participant_by_role(event_id, role)

        if not username:
            raise HTTPException(
                status_code=404,
                detail=f"No participant with role '{role}' for event {event_id}"
            )

        return username