from sqlalchemy.orm import Session
from typing import List, Optional
from api.badges.badges_model import Badge
from api.badges.user_badges_model import UserBadge
from api.badges.badges_schema import BadgeCreate

class BadgeService:
    def __init__(self, db: Session):
        self.db = db

    def list_badges(self) -> List[Badge]:
        return self.db.query(Badge).order_by(Badge.id).all()

    def get_badge(self, badge_id: int) -> Optional[Badge]:
        return self.db.query(Badge).filter(Badge.id == badge_id).first()

    def create_badge(self, badge_in: BadgeCreate) -> Badge:
        badge = Badge(**badge_in.dict())
        self.db.add(badge)
        self.db.commit()
        self.db.refresh(badge)
        return badge
    
    def assign_badge_to_user(
        db: Session,
        user_id: int,
        badge_id: int
        ) -> UserBadge:
        if user_has_badge(db, user_id, badge_id):
            return db.query(UserBadge).filter_by(user_id=user_id, badge_id=badge_id).one()
        ub = UserBadge(user_id=user_id, badge_id=badge_id)
        db.add(ub)
        db.commit()
        db.refresh(ub)
        return ub

    def list_user_badges(self, user_id: int) -> List[UserBadge]:
        return (
            self.db.query(UserBadge)
              .filter(UserBadge.user_id == user_id)
              .order_by(UserBadge.earned_at.desc())
              .all()
        )
        
        
def user_has_badge(db: Session, user_id: int, badge_id: int) -> bool:
        return (
        db.query(UserBadge)
          .filter_by(user_id=user_id, badge_id=badge_id)
          .first()
          is not None
        )