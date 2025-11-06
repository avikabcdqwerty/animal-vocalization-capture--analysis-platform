import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .models import User, get_user_by_id

# Logger setup
logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)

# OAuth2 config
OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
JWT_SECRET_KEY = "REPLACE_WITH_SECURE_RANDOM_KEY"  # Should be set via env var
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60

# RBAC roles
ROLE_RESEARCHER = "researcher"
ROLE_ADMIN = "admin"
SUPPORTED_ROLES = [ROLE_RESEARCHER, ROLE_ADMIN]

class TokenData(BaseModel):
    user_id: Optional[int] = None
    roles: List[str] = []
    exp: Optional[int] = None

class AuthError(HTTPException):
    """
    Custom authentication/authorization error for consistent error handling.
    """
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.debug(f"Created JWT for user_id={data.get('user_id')}")
    return encoded_jwt

def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT access token.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        roles: List[str] = payload.get("roles", [])
        exp: int = payload.get("exp")
        if user_id is None or not roles:
            logger.warning("JWT missing user_id or roles")
            raise AuthError("Invalid authentication credentials")
        return TokenData(user_id=user_id, roles=roles, exp=exp)
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise AuthError("Could not validate credentials")

async def get_current_user(token: str = Depends(OAUTH2_SCHEME)) -> User:
    """
    Dependency to get the current authenticated user from JWT.
    """
    token_data = decode_access_token(token)
    user = get_user_by_id(token_data.user_id)
    if not user:
        logger.warning(f"User not found: {token_data.user_id}")
        raise AuthError("User not found")
    if not user.is_active:
        logger.warning(f"Inactive user: {user.id}")
        raise AuthError("Inactive user")
    user.roles = token_data.roles
    return user

def require_roles(required_roles: List[str]):
    """
    Dependency factory for RBAC enforcement.
    Usage: Depends(require_roles(["researcher"]))
    """
    async def role_checker(user: User = Depends(get_current_user)):
        if not any(role in user.roles for role in required_roles):
            logger.warning(f"User {user.id} lacks required roles: {required_roles}")
            raise AuthError("Insufficient permissions", status.HTTP_403_FORBIDDEN)
        return user
    return role_checker

def get_current_active_researcher(user: User = Depends(get_current_user)) -> User:
    """
    Dependency for endpoints restricted to researchers.
    """
    if ROLE_RESEARCHER not in user.roles:
        logger.warning(f"User {user.id} is not a researcher")
        raise AuthError("Researcher access required", status.HTTP_403_FORBIDDEN)
    return user

def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency for endpoints restricted to admins.
    """
    if ROLE_ADMIN not in user.roles:
        logger.warning(f"User {user.id} is not an admin")
        raise AuthError("Admin access required", status.HTTP_403_FORBIDDEN)
    return user

def get_token_from_request(request: Request) -> Optional[str]:
    """
    Utility to extract JWT token from Authorization header.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None

# Exported symbols
__all__ = [
    "OAUTH2_SCHEME",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "require_roles",
    "get_current_active_researcher",
    "get_current_admin",
    "AuthError",
    "ROLE_RESEARCHER",
    "ROLE_ADMIN",
    "SUPPORTED_ROLES",
    "get_token_from_request",
]