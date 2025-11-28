"""
Base service class with common optimized patterns
"""
from typing import Type, TypeVar, Optional, List, Any, Dict, Generic
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from fastapi import HTTPException, status
from utils.database_utils import DatabaseUtils
from utils.cache_utils import cache_result, cache_user_result

T = TypeVar('T')


class BaseService(Generic[T]):
    """Base service class with common CRUD operations and optimizations"""
    
    def __init__(self, db: Session, model_class: Type[T]):
        self.db = db
        self.model_class = model_class
        self.db_utils = DatabaseUtils()
    
    def get_by_id(self, obj_id: Any) -> Optional[T]:
        """Get object by ID"""
        return self.db.query(self.model_class).filter(
            self.model_class.id == obj_id
        ).first()
    
    def get_by_id_or_404(self, obj_id: Any) -> T:
        """Get object by ID or raise 404"""
        return self.db_utils.get_by_id_or_404(self.db, self.model_class, obj_id)
    
    def get_all(
        self, 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: str = 'desc'
    ) -> List[T]:
        """Get all objects with optional pagination and ordering"""
        query = self.db.query(self.model_class)
        
        # Apply ordering
        if order_by:
            column = getattr(self.model_class, order_by, None)
            if column:
                if order_direction.lower() == 'asc':
                    query = query.order_by(asc(column))
                else:
                    query = query.order_by(desc(column))
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def create(self, data: Dict[str, Any]) -> T:
        """Create new object"""
        obj = self.model_class(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def update(self, obj_id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update object by ID"""
        obj = self.get_by_id(obj_id)
        if not obj:
            return None
        
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def delete(self, obj_id: Any) -> bool:
        """Delete object by ID"""
        obj = self.get_by_id(obj_id)
        if not obj:
            return False
        
        self.db.delete(obj)
        self.db.commit()
        return True
    
    def exists(self, **filters) -> bool:
        """Check if object exists with given filters"""
        return self.db_utils.exists(self.db, self.model_class, **filters)
    
    def count(self, **filters) -> int:
        """Count objects with given filters"""
        return self.db_utils.count(self.db, self.model_class, **filters)
    
    def paginate(
        self, 
        page: int = 1, 
        per_page: int = 50, 
        **filters
    ) -> Dict[str, Any]:
        """Paginate query results"""
        query = self.db.query(self.model_class)
        if filters:
            query = query.filter_by(**filters)
        
        return self.db_utils.paginate_query(query, page, per_page)
    
    def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """Bulk create objects"""
        return self.db_utils.bulk_create(self.db, self.model_class, data_list)
    
    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update objects"""
        return self.db_utils.bulk_update(self.db, self.model_class, updates)


class CachedService(BaseService[T]):
    """Service with caching capabilities"""
    
    def __init__(self, db: Session, model_class: Type[T], cache_ttl: int = 300):
        super().__init__(db, model_class)
        self.cache_ttl = cache_ttl
    
    @cache_result(expiry_seconds=300)
    def get_by_id_cached(self, obj_id: Any) -> Optional[T]:
        """Get object by ID with caching"""
        return self.get_by_id(obj_id)
    
    @cache_result(expiry_seconds=600)
    def get_all_cached(
        self, 
        limit: Optional[int] = None, 
        offset: Optional[int] = None
    ) -> List[T]:
        """Get all objects with caching"""
        return self.get_all(limit=limit, offset=offset)
    
    def create_and_invalidate_cache(self, data: Dict[str, Any]) -> T:
        """Create object and invalidate related caches"""
        obj = self.create(data)
        # Invalidate cache patterns
        self._invalidate_cache_patterns()
        return obj
    
    def update_and_invalidate_cache(self, obj_id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update object and invalidate related caches"""
        obj = self.update(obj_id, data)
        if obj:
            self._invalidate_cache_patterns()
        return obj
    
    def delete_and_invalidate_cache(self, obj_id: Any) -> bool:
        """Delete object and invalidate related caches"""
        success = self.delete(obj_id)
        if success:
            self._invalidate_cache_patterns()
        return success
    
    def _invalidate_cache_patterns(self):
        """Invalidate cache patterns for this service"""
        from utils.cache_utils import cache_manager
        # Invalidate caches related to this model
        cache_manager.delete_pattern(f"cache:*{self.model_class.__name__.lower()}*")


class UserService(CachedService):
    """Optimized user service with caching"""
    
    def __init__(self, db: Session):
        from api.user.user_model import User
        super().__init__(db, User, cache_ttl=600)
    
    @cache_user_result(expiry_seconds=300)
    def get_user_with_relations(self, user_id: int):
        """Get user with eagerly loaded relationships"""
        from sqlalchemy.orm import joinedload
        from api.user.user_model import User
        
        return (
            self.db.query(User)
            .options(
                joinedload(User.details),
                joinedload(User.user_roles).joinedload('role')
            )
            .filter(User.id == user_id)
            .first()
        )
    
    @cache_result(expiry_seconds=1800)  # 30 minutes
    def get_leaderboard(self, limit: int = 10):
        """Get user leaderboard with caching"""
        from api.user.user_model import User
        
        return (
            self.db.query(User)
            .filter(User.is_verified == True)
            .order_by(desc(User.points))
            .limit(limit)
            .all()
        )
    
    def authenticate_user(self, email: str, password: str):
        """Authenticate user with optimized query"""
        from api.user.user_model import User
        from api.user.user_service import verify_password
        
        user = (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )
        
        if not user or not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Email or password incorrect"}
            )
        
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "NOT_VERIFIED", "message": "Account is registered but not verified.", "email": email}
            )
        
        return user


class EventService(CachedService):
    """Optimized event service"""
    
    def __init__(self, db: Session):
        from api.cleanup_events.cleanup_events_model import CleanupEvent
        super().__init__(db, CleanupEvent, cache_ttl=900)  # 15 minutes
    
    def get_events_with_participants(self, limit: int = 50, offset: int = 0):
        """Get events with participant counts"""
        from sqlalchemy import func
        from api.cleanup_events.cleanup_events_model import CleanupEvent
        from api.cleanup_events.event_join_model import EventJoin
        
        return (
            self.db.query(
                CleanupEvent,
                func.count(EventJoin.id).label('participant_count')
            )
            .outerjoin(EventJoin)
            .group_by(CleanupEvent.id)
            .order_by(desc(CleanupEvent.scheduled_date))
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    @cache_result(expiry_seconds=3600)  # 1 hour
    def get_event_statistics(self):
        """Get cached event statistics"""
        from sqlalchemy import func
        from api.cleanup_events.cleanup_events_model import CleanupEvent
        from api.cleanup_events.event_join_model import EventJoin
        
        total_events = self.db.query(func.count(CleanupEvent.id)).scalar()
        total_participants = self.db.query(func.count(EventJoin.id)).scalar()
        
        return {
            'total_events': total_events,
            'total_participants': total_participants,
            'avg_participants_per_event': total_participants / total_events if total_events > 0 else 0
        }