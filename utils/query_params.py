# utils/query_params.py

from typing import Generic, Type, TypeVar, Optional
from fastapi import Query
from sqlalchemy import asc, desc
from sqlalchemy.orm import Query as SAQuery
from pydantic import BaseModel

ModelT = TypeVar("ModelT")

class QueryParams(BaseModel, Generic[ModelT]):
    limit: Optional[int] = Query(None, ge=1, le=200)
    offset: Optional[int] = Query(None, ge=0)
    sort_by: str = Query("id")
    sort_order: str = Query("desc", regex="^(asc|desc)$")

    def apply(self, query: SAQuery, model: Type[ModelT]) -> SAQuery:
        # Ordering
        col = getattr(model, self.sort_by, None)
        if not col:
            raise ValueError(f"Invalid sort_by column: {self.sort_by!r}")
        query = query.order_by(asc(col) if self.sort_order == "asc" else desc(col))

        # Pagination only if provided
        if self.offset is not None:
            query = query.offset(self.offset)
        if self.limit is not None:
            query = query.limit(self.limit)

        return query
