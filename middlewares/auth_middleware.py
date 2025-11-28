from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session
from config.settings import settings
from database.session import get_db
from api.user.user_model import User
from api.roles.user_roles.user_roles_model import UserRole
from api.roles.roles_model import Role
from api.roles.permissions.role_permissions.role_permissions_model import RolePermission
from api.roles.permissions.permissions_model import Permission

SECRET_KEY = settings.SECRET_KEY
security   = HTTPBearer()

def auth_middleware(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded.get("id")
        if not user_id:
            # token was structurally OK but payload missing
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Optimized single query to get user with roles and permissions
        from sqlalchemy.orm import joinedload
        
        user = (
            db.query(User)
            .options(
                joinedload(User.roles).joinedload(Role.permissions)
            )
            .filter(User.id == user_id)
            .first()
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not verified"
            )
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User blocked"
            )

        # Extract roles and permissions from loaded relationships
        roles = []
        permissions = set()  # Use set to avoid duplicates
        
        for role in user.roles:
            roles.append(role.name)
            for permission in role.permissions:
                permissions.add(permission.name)
        
        permissions = list(permissions)  # Convert back to list

        return {
            "id": user.id,
            "name": user.username,
            "is_verified": user.is_verified,
            "status": user.status,
            "roles": roles,
            "permissions": permissions
        }

    except jwt.ExpiredSignatureError:
        # expired token → 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        # any other decode error → 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
