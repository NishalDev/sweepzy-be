"""
Database utilities and common operations to reduce code duplication
"""
from typing import Type, TypeVar, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

T = TypeVar('T')


class DatabaseUtils:
    """Utility class for common database operations"""
    
    @staticmethod
    def get_or_404(db: Session, model_class: Type[T], **filters) -> T:
        """
        Get a single object by filters or raise 404 error
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            **filters: Filter conditions
            
        Returns:
            Model instance
            
        Raises:
            HTTPException: 404 if object not found
        """
        obj = db.query(model_class).filter_by(**filters).first()
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model_class.__name__} not found"
            )
        return obj
    
    @staticmethod
    def get_by_id_or_404(db: Session, model_class: Type[T], obj_id: Any) -> T:
        """
        Get object by ID or raise 404 error
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            obj_id: Object ID
            
        Returns:
            Model instance
            
        Raises:
            HTTPException: 404 if object not found
        """
        obj = db.query(model_class).filter(model_class.id == obj_id).first()
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model_class.__name__} not found"
            )
        return obj
    
    @staticmethod
    def get_batch_by_ids(db: Session, model_class: Type[T], ids: List[Any]) -> List[T]:
        """
        Get multiple objects by IDs in a single query
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            ids: List of IDs
            
        Returns:
            List of model instances
        """
        if not ids:
            return []
        return db.query(model_class).filter(model_class.id.in_(ids)).all()
    
    @staticmethod
    def paginate_query(
        query,
        page: int = 1,
        per_page: int = 50,
        max_per_page: int = 200
    ) -> Dict[str, Any]:
        """
        Paginate a SQLAlchemy query
        
        Args:
            query: SQLAlchemy query object
            page: Page number (1-based)
            per_page: Items per page
            max_per_page: Maximum items per page
            
        Returns:
            Dictionary with pagination info and items
        """
        # Limit per_page to prevent abuse
        per_page = min(per_page, max_per_page)
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get total count (only if needed)
        total = query.count() if page == 1 else None
        
        # Get items
        items = query.offset(offset).limit(per_page).all()
        
        # Check if there are more items
        has_next = len(items) == per_page
        
        return {
            'items': items,
            'page': page,
            'per_page': per_page,
            'total': total,
            'has_next': has_next,
            'has_prev': page > 1
        }
    
    @staticmethod
    def cursor_paginate(
        query,
        cursor_column,
        cursor_value: Optional[Any] = None,
        limit: int = 50,
        direction: str = 'forward'
    ) -> Dict[str, Any]:
        """
        Cursor-based pagination for better performance on large datasets
        
        Args:
            query: SQLAlchemy query object
            cursor_column: Column to use for cursor
            cursor_value: Cursor value for pagination
            limit: Number of items to return
            direction: 'forward' or 'backward'
            
        Returns:
            Dictionary with pagination info and items
        """
        if cursor_value:
            if direction == 'forward':
                query = query.filter(cursor_column > cursor_value)
            else:
                query = query.filter(cursor_column < cursor_value)
        
        # Get one extra item to check if there are more
        items = query.limit(limit + 1).all()
        has_more = len(items) > limit
        
        if has_more:
            items = items[:-1]
        
        next_cursor = None
        if items and has_more:
            next_cursor = getattr(items[-1], cursor_column.name)
        
        return {
            'items': items,
            'has_more': has_more,
            'next_cursor': next_cursor,
            'limit': limit
        }
    
    @staticmethod
    def bulk_create(db: Session, model_class: Type[T], data_list: List[Dict[str, Any]]) -> List[T]:
        """
        Bulk create objects for better performance
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            data_list: List of dictionaries with object data
            
        Returns:
            List of created objects
        """
        objects = [model_class(**data) for data in data_list]
        db.add_all(objects)
        db.commit()
        return objects
    
    @staticmethod
    def bulk_update(
        db: Session, 
        model_class: Type[T], 
        updates: List[Dict[str, Any]], 
        id_field: str = 'id'
    ) -> int:
        """
        Bulk update objects for better performance
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            updates: List of dictionaries with update data (must include id_field)
            id_field: Name of the ID field
            
        Returns:
            Number of updated records
        """
        if not updates:
            return 0
        
        # Use bulk_update_mappings for better performance
        db.bulk_update_mappings(model_class, updates)
        db.commit()
        return len(updates)
    
    @staticmethod
    def safe_delete(db: Session, obj: T) -> bool:
        """
        Safely delete an object with error handling
        
        Args:
            db: Database session
            obj: Object to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            db.delete(obj)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    @staticmethod
    def exists(db: Session, model_class: Type[T], **filters) -> bool:
        """
        Check if object exists with given filters
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            **filters: Filter conditions
            
        Returns:
            True if object exists, False otherwise
        """
        return db.query(
            db.query(model_class).filter_by(**filters).exists()
        ).scalar()
    
    @staticmethod
    def count(db: Session, model_class: Type[T], **filters) -> int:
        """
        Count objects with given filters
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            **filters: Filter conditions
            
        Returns:
            Count of objects
        """
        query = db.query(model_class)
        if filters:
            query = query.filter_by(**filters)
        return query.count()


# Convenience functions for common operations
def get_user_or_404(db: Session, user_id: int):
    """Get user by ID or raise 404"""
    from api.user.user_model import User
    return DatabaseUtils.get_by_id_or_404(db, User, user_id)


def get_users_batch(db: Session, user_ids: List[int]):
    """Get multiple users by IDs in a single query"""
    from api.user.user_model import User
    return DatabaseUtils.get_batch_by_ids(db, User, user_ids)