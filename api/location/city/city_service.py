# api/cities/cities_service.py
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.location.city.city_model import City


def _normalize_name(name: str) -> str:
    return name.strip()


def create_city(db: Session, city_data: dict) -> City:
    """
    Create a new city. Raises HTTPException(400) if a case-insensitive duplicate exists.
    Returns the created City instance.
    """
    # Make sure we get a plain string
    name = city_data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="City name is required")
    name = _normalize_name(name)

    try:
        # Case-insensitive uniqueness check
        existing = db.query(City).filter(func.lower(City.name) == name.lower()).one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="City with this name already exists")

        # Create the City object
        city = City(name=name)
        db.add(city)
        db.commit()
        db.refresh(city)  # ensures `created_at` is loaded
        return city

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create city: {exc}") from exc

def get_cities(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Return a paginated list of cities with total_count.
    """
    try:
        query = db.query(City)
        if search:
            query = query.filter(City.name.ilike(f"%{search}%"))

        total_count = query.with_entities(func.count()).scalar() or 0

        cities: List[City] = (
            query.order_by(City.name)
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {"total_count": total_count, "cities": cities}
    except Exception as exc:
        # optionally log
        raise HTTPException(status_code=500, detail="Failed to fetch cities") from exc


def get_city(db: Session, city_id: int) -> City:
    """
    Fetch a single city by id. Raises 404 if not found.
    """
    try:
        city = db.query(City).filter(City.id == city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=404, detail="City not found")
        return city
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch city") from exc


def update_city(db: Session, city_id: int, city_data: dict) -> City:
    """
    Update a city's name. Validates uniqueness. Raises 404 if missing, 400 if conflict.
    """
    payload = jsonable_encoder(city_data)
    new_name = _normalize_name(payload.get("name", ""))

    if not new_name:
        raise HTTPException(status_code=400, detail="City name is required")

    try:
        city = db.query(City).filter(City.id == city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=404, detail="City not found")

        conflict = (
            db.query(City)
              .filter(func.lower(City.name) == new_name.lower(), City.id != city_id)
              .one_or_none()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="Another city with this name already exists")

        city.name = new_name
        db.add(city)
        db.commit()
        db.refresh(city)
        return city
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update city") from exc


def delete_city(db: Session, city_id: int) -> None:
    """
    Delete a city. Raises 404 if not found.
    Note: cascading behavior depends on your FK rules in DB (landmarks/reports).
    """
    try:
        city = db.query(City).filter(City.id == city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=404, detail="City not found")

        db.delete(city)
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete city") from exc
