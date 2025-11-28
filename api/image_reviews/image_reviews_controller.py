from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from config.database import get_db
from api.image_reviews.image_reviews_service import (
    create_image_review,
    get_image_review,
    list_image_reviews
)
from api.image_reviews.image_reviews_schema import ImageReviewCreate, ImageReviewResponse

def create_image_review_controller(review_data: ImageReviewCreate, db: Session = Depends(get_db)) -> ImageReviewResponse:
    review = create_image_review(db, review_data.dict())
    if not review:
        raise HTTPException(status_code=400, detail="Failed to create image review")
    return review

def get_image_review_controller(review_id: UUID, db: Session = Depends(get_db)) -> ImageReviewResponse:
    review = get_image_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Image review not found")
    return review

def list_image_reviews_controller(db: Session = Depends(get_db)):
    reviews = list_image_reviews(db)
    return reviews
