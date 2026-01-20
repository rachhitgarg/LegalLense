"""
auth.py - JWT-based authentication and RBAC.

Roles:
- practitioner: Full access, advanced search, citation export
- student: Search, summaries, learning mode
"""

import os
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()


class User(BaseModel):
    """User model."""
    user_id: str
    username: str
    role: str  # "practitioner" or "student"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user_id
    username: str
    role: str
    exp: datetime


def create_token(user: User) -> str:
    """Create a JWT token for the user."""
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """Dependency to get the current authenticated user."""
    return decode_token(credentials.credentials)


def require_role(allowed_roles: list[str]):
    """Dependency factory to require specific roles."""
    async def role_checker(user: TokenPayload = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' not authorized. Required: {allowed_roles}",
            )
        return user
    return role_checker


# Pre-built role dependencies
require_practitioner = require_role(["practitioner"])
require_student_or_practitioner = require_role(["student", "practitioner"])


# Demo users for testing (in production, use a database)
DEMO_USERS = {
    "practitioner_demo": User(
        user_id="p1",
        username="practitioner_demo",
        role="practitioner",
    ),
    "student_demo": User(
        user_id="s1",
        username="student_demo",
        role="student",
    ),
}


def authenticate_demo(username: str, password: str) -> Optional[User]:
    """Authenticate demo users. In production, use proper auth."""
    if password == "demo123" and username in DEMO_USERS:
        return DEMO_USERS[username]
    return None
