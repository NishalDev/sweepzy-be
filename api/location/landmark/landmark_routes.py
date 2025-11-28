# api/landmarks/landmarks_routes.py
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from middlewares.role_middleware import role_middleware

from api.location.landmark.landmark_schema import LandmarkCreate, LandmarkRead
from api.location.landmark.landmark_service import (
    create_landmark,
    get_landmarks,
    get_landmark,
    update_landmark,
    delete_landmark,
    get_landmarks_for_city,
)

router = APIRouter(prefix="/landmarks", tags=["Landmarks"])


@router.post("/", response_model=LandmarkRead, summary="Create a new landmark", dependencies=[Depends(role_middleware(required_roles=["admin"]))])
def create_landmark_endpoint(
    payload: LandmarkCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    """
    Create a new landmark for a city. (Admin only)
    """
    return create_landmark(db, payload.model_dump())


@router.get("/", summary="List landmarks (paginated)")
def list_landmarks_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    city_id: Optional[int] = Query(None, description="Filter by city id"),
    search: Optional[str] = Query(None, description="Search by landmark name"),
    db: Session = Depends(get_db),
):
    """
    Returns a dict with `total_count` and `landmarks` (list of Landmark models).
    """
    return get_landmarks(db=db, limit=limit, offset=offset, city_id=city_id, search=search)


@router.get("/{landmark_id}", response_model=LandmarkRead, summary="Get a landmark by id")
def get_landmark_endpoint(
    landmark_id: int,
    db: Session = Depends(get_db),
):
    """
    Fetch a landmark by id.
    """
    return get_landmark(db, landmark_id)


@router.put("/{landmark_id}", response_model=LandmarkRead, summary="Update a landmark")
def update_landmark_endpoint(
    landmark_id: int,
    payload: LandmarkCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
    _ = Depends(role_middleware("admin")),  # admin only
):
    """
    Update a landmark's name and/or city. (Admin only)
    """
    return update_landmark(db, landmark_id, payload.model_dump())


@router.delete("/{landmark_id}", summary="Delete a landmark")
def delete_landmark_endpoint(
    landmark_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
    _ = Depends(role_middleware("admin")),  # admin only
):
    """
    Delete a landmark. (Admin only)
    """
    delete_landmark(db, landmark_id)
    return {"detail": "Landmark deleted"}


@router.get("/by_city/{city_id}", response_model=List[LandmarkRead], summary="List all landmarks for a city")
def landmarks_for_city_endpoint(
    city_id: int,
    db: Session = Depends(get_db),
):
    """
    Useful for UI dropdowns: returns all landmarks for the given city.
    """
    return get_landmarks_for_city(db, city_id)
