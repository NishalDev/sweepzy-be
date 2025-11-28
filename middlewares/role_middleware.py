from fastapi import HTTPException, Depends
from typing import List, Dict, Any
from fastapi import Request  # only import if you actually need it in your route
from middlewares.auth_middleware import auth_middleware
def role_middleware(
    required_roles: List[str] = None,
    required_permissions: List[str] = None
):
    # avoid mutable default args
    required_roles = required_roles or []
    required_permissions = required_permissions or []

    def dependency(user: Dict[str, Any] = Depends(auth_middleware)):
        # auth_middleware already raises 401/403 for bad tokens, so user is guaranteed
        user_roles = user.get("roles", [])
        user_permissions = user.get("permissions", [])

        # 1️⃣ Check roles (if any)
        if required_roles and not any(r in user_roles for r in required_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: requires one of roles {required_roles}"
            )

        # 2️⃣ Check permissions (if any)
        if required_permissions and not all(p in user_permissions for p in required_permissions):
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: requires permissions {required_permissions}"
            )

        return user

    return dependency
