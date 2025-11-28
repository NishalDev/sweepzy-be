# api/cities/cities_routes.py
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from middlewares.role_middleware import role_middleware

from api.location.city.city_schema import CityCreate, CityRead
from api.location.city.city_controller import (
    create_city_controller,
    get_cities_controller,
    get_city_controller,
    update_city_controller,
    delete_city_controller,
)

router = APIRouter(prefix="/cities", tags=["Cities"])


@router.post(
    "/",
    response_model=CityRead,
    summary="Create a new city",
    dependencies=[Depends(role_middleware(required_roles=["admin"]))]
)
def create_city_endpoint(
    city_in: CityCreate,
    db: Session = Depends(get_db),
):
    return create_city_controller(db, city_in)


@router.get("/", summary="List cities (paginated)")
def list_cities_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return get_cities_controller(db=db, limit=limit, offset=offset, search=search)

@router.get("/{city_id}", response_model=CityRead, summary="Get a city by id")
def get_city_endpoint(
    city_id: int,
    db: Session = Depends(get_db),
):
    """
    Fetch a city by id.
    """
    return get_city_controller(db, city_id)


@router.put("/{city_id}", response_model=CityRead, summary="Update a city")
def update_city_endpoint(
    city_id: int,
    city_in: CityCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
    _ = Depends(role_middleware("admin")),  # admin only
):
    """
    Update a city's name. (Admin only)
    """
    return update_city_controller(db, city_id, city_in.model_dump())


@router.delete("/{city_id}", summary="Delete a city")
def delete_city_endpoint(
    city_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
    _ = Depends(role_middleware("admin")),  # admin only
):
    """
    Delete a city. (Admin only)
    """
    delete_city_controller(db, city_id)
    return {"detail": "City deleted"}
