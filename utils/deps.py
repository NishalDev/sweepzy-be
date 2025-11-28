from typing import Optional
from fastapi import Request
from .query_params import QueryParams  # your QueryParams pydantic model

async def optional_pagination(request: Request) -> Optional[QueryParams]:
    """
    Return QueryParams if any pagination keys are present in the query string,
    otherwise return None.
    """
    qp = request.query_params
    # decide which query keys you consider as "pagination requested"
    pagination_keys = {"limit", "offset", "page", "per_page", "sort_by", "sort_order"}
    if any(k in qp for k in ("limit", "offset")):  # require at least limit/offset
        # instantiate QueryParams from the query params dict (pydantic will coerce)
        try:
            return QueryParams(**qp)
        except Exception:
            # Let FastAPI handle validation errors if you want -> raise HTTPException
            return QueryParams(**{})  # fallback to defaults (optional)
    return None
