from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from api.image_reviews.image_reviews_controller import (
    create_image_review_controller,
    get_image_review_controller,
    list_image_reviews_controller
)
from api.image_reviews.image_reviews_schema import ImageReviewCreate, ImageReviewResponse
from config.database import get_db

router = APIRouter(prefix="/image_reviews", tags=["Image Reviews"])

@router.post("/", response_model=ImageReviewResponse)
def create_image_review_endpoint(review: ImageReviewCreate, db: Session = Depends(get_db)):
    return create_image_review_controller(review, db)

@router.get("/{review_id}", response_model=ImageReviewResponse)
def get_image_review_endpoint(review_id: UUID, db: Session = Depends(get_db)):
    return get_image_review_controller(review_id, db)

@router.get("/", response_model=List[ImageReviewResponse])
def list_image_reviews_endpoint(db: Session = Depends(get_db)):
    return list_image_reviews_controller(db)
