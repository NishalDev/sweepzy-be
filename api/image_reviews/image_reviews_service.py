from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from api.image_reviews.image_reviews_model import ImageReview

def create_image_review(db: Session, review_data: dict) -> ImageReview:
    new_review = ImageReview(**review_data)
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

def get_image_review(db: Session, review_id: UUID) -> ImageReview:
    return db.query(ImageReview).filter(ImageReview.id == review_id).first()

def list_image_reviews(db: Session) -> List[ImageReview]:
    return db.query(ImageReview).all()
