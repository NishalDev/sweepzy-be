# api/landmarks/landmarks_controller.py
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.location.landmark.landmark_model import Landmark
from api.location.city.city_model import City
from api.location.landmark.landmark_schema import LandmarkCreate  # LandmarkRead not required here

def create_landmark_controller(db: Session, landmark_data: LandmarkCreate) -> Landmark:
    """
    Create a new landmark linked to an existing city.
    Raises 400 if city does not exist or duplicate landmark name exists within the same city.
    """
    try:
        name = landmark_data.name.strip()
        city_id = landmark_data.city_id

        city = db.query(City).filter(City.id == city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=400, detail="City does not exist")

        # Ensure unique landmark name within city (case-insensitive)
        existing = (
            db.query(Landmark)
            .filter(Landmark.city_id == city_id, func.lower(Landmark.name) == name.lower())
            .one_or_none()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Landmark with this name already exists in the city")

        lm = Landmark(name=name, city_id=city_id)
        db.add(lm)
        db.commit()
        db.refresh(lm)
        return lm
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create landmark") from exc


def get_landmarks_controller(
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


def get_landmark_controller(db: Session, landmark_id: int) -> Landmark:
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


def update_landmark_controller(db: Session, landmark_id: int, landmark_data: LandmarkCreate) -> Landmark:
    """
    Update a landmark's name and/or city. Validates city existence and uniqueness of name within the city.
    """
    try:
        lm = db.query(Landmark).filter(Landmark.id == landmark_id).one_or_none()
        if not lm:
            raise HTTPException(status_code=404, detail="Landmark not found")

        new_name = landmark_data.name.strip()
        new_city_id = landmark_data.city_id

        # validate target city exists
        city = db.query(City).filter(City.id == new_city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=400, detail="Target city does not exist")

        # check for name conflict within the target city
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
        raise HTTPException(status_code=500, detail="Failed to update landmark") from exc


def delete_landmark_controller(db: Session, landmark_id: int) -> None:
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
        raise HTTPException(status_code=500, detail="Failed to delete landmark") from exc
