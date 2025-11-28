# api/landmarks/landmarks_service.py
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from api.location.landmark.landmark_model import Landmark
from api.location.city.city_model import City


def _normalize_name(name: str) -> str:
    return name.strip()



def create_landmark(db: Session, landmark_data: Dict[str, Any]) -> Landmark:
    """
    Create a new landmark linked to an existing city.
    Raises 400 if city doesn't exist or duplicate within the same city.
    """
    payload = jsonable_encoder(landmark_data)
    raw_name = payload.get("name")
    raw_city_id = payload.get("city_id")

    # validate name
    if not raw_name or not isinstance(raw_name, str) or not raw_name.strip():
        raise HTTPException(status_code=400, detail="Landmark name is required")
    name = _normalize_name(raw_name)

    # validate city_id and coerce to int
    if raw_city_id is None:
        raise HTTPException(status_code=400, detail="city_id is required")
    try:
        city_id = int(raw_city_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="city_id must be an integer")

    try:
        # ensure target city exists
        city = db.query(City).filter(City.id == city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=400, detail="City does not exist")

        # uniqueness check (case-insensitive) within the city
        existing = (
            db.query(Landmark)
              .filter(Landmark.city_id == city_id, func.lower(Landmark.name) == name.lower())
              .one_or_none()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Landmark with this name already exists in the city")

        # create and persist
        lm = Landmark(name=name, city_id=city_id)
        db.add(lm)
        db.commit()
        db.refresh(lm)  # ensure server defaults (created_at) are loaded
        return lm

    except HTTPException:
        # re-raise client errors
        raise
    except IntegrityError as ie:
        db.rollback()
        # nice to hint at unique constraint/race conditions
        raise HTTPException(status_code=500, detail=f"Database integrity error: {ie.orig.pgerror if hasattr(ie, 'orig') else str(ie)}") from ie
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create landmark: {exc}") from exc

def get_landmarks(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    city_id: Optional[int] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Return paginated list of landmarks. Optional filter by city_id and search by name.
    """
    try:
        query = db.query(Landmark)
        if city_id is not None:
            query = query.filter(Landmark.city_id == city_id)
        if search:
            query = query.filter(Landmark.name.ilike(f"%{search}%"))

        total_count = query.with_entities(func.count()).scalar() or 0

        landmarks: List[Landmark] = (
            query.order_by(Landmark.name)
                 .offset(offset)
                 .limit(limit)
                 .all()
        )

        return {"total_count": total_count, "landmarks": landmarks}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch landmarks") from exc


def get_landmark(db: Session, landmark_id: int) -> Landmark:
    """
    Fetch a single landmark by id. Raises 404 if not found.
    """
    try:
        lm = db.query(Landmark).filter(Landmark.id == landmark_id).one_or_none()
        if not lm:
            raise HTTPException(status_code=404, detail="Landmark not found")
        return lm
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch landmark") from exc


def update_landmark(db: Session, landmark_id: int, landmark_data: dict) -> Landmark:
    """
    Update a landmark's name and/or city. Validates target city and uniqueness in target city.
    """
    payload = jsonable_encoder(landmark_data)
    new_name = _normalize_name(payload.get("name", ""))
    new_city_id = payload.get("city_id")

    if not new_name:
        raise HTTPException(status_code=400, detail="Landmark name is required")
    if not new_city_id:
        raise HTTPException(status_code=400, detail="city_id is required")

    try:
        lm = db.query(Landmark).filter(Landmark.id == landmark_id).one_or_none()
        if not lm:
            raise HTTPException(status_code=404, detail="Landmark not found")

        city = db.query(City).filter(City.id == new_city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=400, detail="Target city does not exist")

        conflict = (
            db.query(Landmark)
              .filter(
                  Landmark.city_id == new_city_id,
                  func.lower(Landmark.name) == new_name.lower(),
                  Landmark.id != landmark_id
              )
              .one_or_none()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="Another landmark with this name already exists in the city")

        lm.name = new_name
        lm.city_id = new_city_id
        db.add(lm)
        db.commit()
        db.refresh(lm)
        return lm
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update landmark") from exc


def delete_landmark(db: Session, landmark_id: int) -> None:
    """
    Delete a landmark. Raises 404 if not found.
    """
    try:
        lm = db.query(Landmark).filter(Landmark.id == landmark_id).one_or_none()
        if not lm:
            raise HTTPException(status_code=404, detail="Landmark not found")

        db.delete(lm)
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete landmark") from exc


def get_landmarks_for_city(db: Session, city_id: int) -> List[Landmark]:
    """
    Return all landmarks for a specific city (useful for dropdowns). Raises 404 if city doesn't exist.
    """
    try:
        city = db.query(City).filter(City.id == city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=404, detail="City not found")

        landmarks: List[Landmark] = (
            db.query(Landmark)
              .filter(Landmark.city_id == city_id)
              .order_by(Landmark.name)
              .all()
        )
        return landmarks
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch landmarks for city") from exc
