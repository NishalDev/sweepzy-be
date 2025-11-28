from fastapi import APIRouter, Depends
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.cleanup_events.event_join_schema import EventJoin, EventJoinCreate, EventParticipantResponse, UsernameOnlyResponse, EventJoinUpdate
from api.cleanup_events.event_join_controller import EventJoinController

router = APIRouter(prefix="/event_joins", tags=["event_joins"])

@router.post("/", response_model=EventJoin)
def create_event_join(
    payload: EventJoinCreate,
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    user_id = current_user["id"]
    return EventJoinController.create_join(payload, db, user_id)

@router.get("/", response_model=List[EventJoin])
def list_event_joins(
    db=Depends(get_db),
    event_id: Optional[int] = None,
    current_user=Depends(auth_middleware)
):
    return EventJoinController.list_joins(db, event_id)

@router.get(
    "/user_details",
    response_model=List[UsernameOnlyResponse],
    summary="List participants for an event by role",
)
def get_user_details_by_role(
    event_id: UUID,
    role: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth_middleware),
):
    """
    Returns the username(s) of participants in `event_id` who have the given `role`.
    """
    # Now calls the staticmethod directly with all three args
    username = EventJoinController.get_participant_by_role(event_id, role, db)
    return [UsernameOnlyResponse(username=username)]

@router.get("/{join_id}", response_model=EventJoin)
def get_event_join(
    join_id: int,
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    return EventJoinController.get_join(join_id, db)

@router.put("/{join_id}", response_model=EventJoin)
def update_event_join(
    join_id: int,
    payload: EventJoinUpdate,
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    return EventJoinController.update_join(join_id, payload, db)

@router.delete("/{join_id}")
def delete_event_join(
    join_id: int,
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    EventJoinController.delete_join(join_id, db)
    return {"detail": "Deleted"}

# @router.get("/user_details", response_model=List[EventParticipantResponse])
# def get_user_details_by_role(
#     db=Depends(get_db),
#     current_user=Depends(auth_middleware)
# ):
#     user_id = current_user["id"]
#     return EventJoinController.get_user_details_by_role(user_id, db)
