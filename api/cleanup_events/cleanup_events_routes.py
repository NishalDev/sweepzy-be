from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from middlewares.role_middleware import role_middleware
from api.cleanup_events.cleanup_events_schema import (
    CleanupEventCreate, CleanupEventUpdate, CleanupEventRead, CleanupEventDetail, CleanupEventSummary, UserJoinedEventOut
)
from api.cleanup_events.cleanup_events_controller import CleanupEventController
from api.litter_groups.litter_groups_schema import ClusterSuggestion
from api.cleanup_events.event_join_schema import (
    EventJoin, EventJoinUpdate, EventParticipantResponse
)
from api.cleanup_events.cleanup_events_model import CleanupEvent
from utils.query_params import QueryParams

router = APIRouter(prefix="/cleanup_events", tags=["cleanup_events"])

@router.get(
    "/joins",
    response_model=List[UserJoinedEventOut],
    summary="List all events the current user has signed up for"
)
def list_my_joins(
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    return CleanupEventController.list_user_joins(db, current_user)

@router.get(
    "/available_groups",
    response_model=List[ClusterSuggestion],
    summary="List automatically detected clusters available for event creation",
)
def available_groups(
    min_reports: int = Query(1, ge=1),
    db=Depends(get_db),
):
    return CleanupEventController.list_available_groups(db, min_reports)


@router.post("/create-event", response_model=CleanupEventRead)
def create_event(
    payload: CleanupEventCreate,
    db=Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    user_id = current_user["id"]
    return CleanupEventController.create_event(payload, db, user_id)

@router.get(
    "/submitted",
    response_model=List[CleanupEventSummary],
    summary="List all events submitted for admin verification",
    dependencies=[Depends(role_middleware(required_roles=["admin"]))]
)
def list_submitted_events(
    params: QueryParams[CleanupEvent] = Depends(),
    db: Session = Depends(get_db)
):
    return CleanupEventController.list_submitted_events(db, params)

@router.get("/join-roles", response_model=List[str])
def join_roles(db=Depends(get_db), current_user=Depends(auth_middleware)):
    return CleanupEventController.list_join_roles(db)

@router.get("/", response_model=List[CleanupEventRead])
def list_events(
    params = Depends(QueryParams[CleanupEvent]),
    db=Depends(get_db),
    litter_group_id: Optional[UUID] = None,
):
    return CleanupEventController.list_events(db, params, litter_group_id)


@router.get("/{event_id}", response_model=CleanupEventRead)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    user_id = current_user["id"]
    event = CleanupEventController.get_event(event_id, db, user_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.put(
    "/{event_id}",
    response_model=CleanupEventRead,
    dependencies=[Depends(role_middleware(required_roles=["admin"]))],
    summary="Update an event (admin only)"
)
def update_event(
    event_id: UUID,
    payload: CleanupEventUpdate,
    db=Depends(get_db),
    current_user:dict = Depends(role_middleware(required_roles=["admin"]))
):
    return CleanupEventController.update_event(event_id, payload, db, current_user)  # pass user_id instead of current_user


@router.delete("/{event_id}")
def delete_event(
    event_id: UUID,
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    return CleanupEventController.delete_event(event_id, db, current_user)


@router.get("/{event_id}/participants", response_model=List[EventParticipantResponse])
def list_event_participants(
    event_id: UUID,
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    return CleanupEventController.list_participants(event_id, db)


@router.put("/{event_id}/participants/{participant_id}", response_model=EventJoin)
def update_participant_status(
    event_id: UUID,
    participant_id: int,
    payload: EventJoinUpdate,
    db=Depends(get_db),
    current_user=Depends(auth_middleware)
):
    return CleanupEventController.update_participant(event_id, participant_id, payload, db, current_user)


@router.get(
    "/submitted/{event_id}",
    response_model=CleanupEventDetail,
    dependencies=[Depends(role_middleware(required_roles=["admin"]))],
    summary="Get one submitted event (with photos & attendance) for admin review"
)
def get_submitted_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(role_middleware(required_roles=["admin"]))
):
    return CleanupEventController.get_submitted_event_details(event_id, db)