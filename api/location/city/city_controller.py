# api/cities/cities_controller.py
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc

from api.location.city.city_model import City
from api.location.city.city_schema import CityCreate  # CityRead not required in controller but used by endpoints

def create_city_controller(db: Session, city_data: CityCreate) -> City:
    """
    Create a new city. Raises 400 if a city with the same name already exists.
    Returns the created City model instance.
    """
    try:
        # normalized name check (avoid duplicates with case differences)
        name = city_data.name.strip()
        existing = db.query(City).filter(func.lower(City.name) == name.lower()).one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="City with this name already exists")

        city = City(name=name)
        db.add(city)
        db.commit()
        db.refresh(city)
        return city
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        print("❌ Failed to create city:", exc)
        raise HTTPException(status_code=500, detail=f"Failed to create city: {exc}") from exc


def get_cities_controller(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None
) -> Dict[str, any]:
    """
    Fetch paginated cities with total count, ordered by name ascending.
    """
    try:
        # 1️⃣ Base query
        query = db.query(City)
        if search:
            query = query.filter(City.name.ilike(f"%{search}%"))

        # 2️⃣ Get total count without order/limit/offset
        total_count = query.with_entities(func.count()).scalar() or 0

        # 3️⃣ Apply ordering, pagination
        cities = (
            query.order_by(asc(City.name))
                 .offset(offset)
                 .limit(limit)
                 .all()
        )

        # 4️⃣ Convert to dict
        cities_data = [{"id": c.id, "name": c.name, "created_at": c.created_at} for c in cities]

        return {"total_count": total_count, "cities": cities_data}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cities: {exc}")
    
def get_city_controller(db: Session, city_id: int) -> City:
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


def update_city_controller(db: Session, city_id: int, city_data: CityCreate) -> City:
    """
    Update a city's name. Raises 404 if city doesn't exist, 400 if name conflict.
    Returns the updated City model instance.
    """
    try:
        city = db.query(City).filter(City.id == city_id).one_or_none()
        if not city:
            raise HTTPException(status_code=404, detail="City not found")

        new_name = city_data.name.strip()
        # Check other city with same name
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
        raise HTTPException(status_code=500, detail="Failed to update city") from exc


def delete_city_controller(db: Session, city_id: int) -> None:
    """
    Delete a city. Raises 404 if not found.
    Note: deletion cascades depend on your FK rules. This returns None on success.
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
        raise HTTPException(status_code=500, detail="Failed to delete city") from exc
