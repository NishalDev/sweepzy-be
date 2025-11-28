import jwt
import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session
from config.settings import settings  # must define SECRET_KEY and ALGORITHM
from api.user.user_model import User

def create_access_token(
    payload: Dict[str, Any],
    expires_hours: int = 1,
) -> str:
    """
    Generate a JWT access token with the given payload and expiration.
    """
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=expires_hours)
    to_encode = payload.copy()
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def create_user_token(
    db: Session,
    user: User,
    expires_hours: int = 1
) -> str:
    """
    Generate a JWT for a User instance, embedding:
      - id
      - username
      - roles (as a list of strings)
      - permissions (deduplicated list)
      - exp (handled by create_access_token)
    """
    # 1️⃣ Grab roles via relationship
    try:
        roles: List[str] = [role.name for role in user.roles]
    except Exception:
        roles = []

    # 2️⃣ Gather permissions from each role
    perms: List[str] = []
    try:
        for role in user.roles:
            perms.extend([p.name for p in role.permissions])
    except Exception:
        pass

    # Remove duplicates
    permissions = list(set(perms))

    # Build the payload (no exp here)
    token_payload: Dict[str, Any] = {
        "id":       user.id,
        "username": user.username,
        "roles":    roles or ["user"],        # default to ["user"] if no roles
        "permissions": permissions,
    }

    # Delegate to create_access_token to set exp+encode
    return create_access_token(token_payload, expires_hours)
