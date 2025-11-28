from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from config.database import get_db
from middlewares.auth_middleware import auth_middleware

from api.litter_groups.litter_groups_schema import (
    LitterGroupCreate,
    LitterGroupUpdate,
    LitterGroupRead,
    ClusterSuggestion
)
from api.litter_groups.litter_groups_controller import LitterGroupController  # ✅ Import the full controller class

router = APIRouter(
    prefix="/litter_groups",
    tags=["litter_groups"]
)

@router.get(
    "/available-groups",
    response_model=List[LitterGroupRead],
    summary="List all available (unlocked) litter groups"
)
def list_available_litter_groups(
    db = Depends(get_db),
):
    """Get all litter groups where is_locked is False."""
    return LitterGroupController.list_available_groups(db)

@router.get(
    "/cluster_suggestions",
    response_model=List[ClusterSuggestion],
    summary="Get suggested clusters of litter reports"
)
def get_cluster_suggestions(
    db = Depends(get_db),
):
    return LitterGroupController.list_suggestions(db)
@router.post(
    "/",
    response_model=LitterGroupRead,
    summary="Create a new litter group"
)
def create_litter_group(
    payload: LitterGroupCreate,
    db = Depends(get_db),
    current_user = Depends(auth_middleware),
):
    user_id = current_user["id"]
    group = LitterGroupController.create_group(payload, db, user_id)
    if not group:
        raise HTTPException(status_code=400, detail="Failed to create group")
    return group


@router.get(
    "/",
    response_model=List[LitterGroupRead],
    summary="List all litter groups for current user"
)
def list_litter_groups(
    db = Depends(get_db),
    current_user = Depends(auth_middleware),
):
    user_id = current_user["id"]
    return LitterGroupController.list_groups(db, user_id)


@router.get(
    "/{group_id}",
    response_model=LitterGroupRead,
    summary="Get a single litter group by ID"
)
def get_litter_group(
    group_id: UUID,
    db = Depends(get_db),
    current_user = Depends(auth_middleware),
):
    user_id = current_user["id"]
    group = LitterGroupController.get_group(group_id, db, user_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.put(
    "/{group_id}",
    response_model=LitterGroupRead,
    summary="Update a litter group"
)
def update_litter_group(
    group_id: UUID,
    payload: LitterGroupUpdate,
    db = Depends(get_db),
    current_user = Depends(auth_middleware),
):
    user_id = current_user["id"]
    group = LitterGroupController.update_group(group_id, payload, db, user_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or not yours")
    return group


@router.delete(
    "/{group_id}",
    summary="Delete a litter group"
)
def delete_litter_group(
    group_id: UUID,
    db = Depends(get_db),
    current_user = Depends(auth_middleware),
):
    user_id = current_user["id"]
    success = LitterGroupController.delete_group(group_id, db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Group not found or not yours")
    return {"detail": "Group deleted"}


@router.post(
    "/create_from_suggestion/{cluster_id}",
    response_model=LitterGroupRead,
    summary="Create a litter group from a suggested cluster"
)
def create_group_from_suggestion(
    cluster_id: int,
    payload: LitterGroupCreate,
    db = Depends(get_db),
    current_user = Depends(auth_middleware),
):
    user_id = current_user["id"]
    return LitterGroupController.create_from_suggestion(cluster_id, payload, db, user_id)

@router.get(
    "/available-groups/{group_id}",
    response_model=LitterGroupRead,
    summary="Get details of an available (unlocked) litter group by ID"
)
def get_available_group_details(
    group_id: UUID,
    db = Depends(get_db),
):
    """Get details of a single available (unlocked) litter group by ID."""
    group = LitterGroupController.get_available_group_by_id(group_id, db)
    if not group:
        raise HTTPException(status_code=404, detail="Available group not found")
    return group


