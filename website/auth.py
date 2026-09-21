import os
import datetime
from typing import Optional, List, Dict, Any
import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, Response

JWT_SECRET = os.getenv("JWT_SECRET", "campusos_jwt_super_secret_signing_key_2026_x99_sec")
JWT_ALGORITHM = "HS256"
JWT_COOKIE_NAME = "campusos_token"
JWT_EXPIRATION_DAYS = 7

# Role Hierarchy levels: hod (3) > teacher (2) > student (1)
ROLE_LEVELS = {
    "student": 1,
    "teacher": 2,
    "hod": 3
}


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Create a signed JWT access token with role and user claims."""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + (
        expires_delta or datetime.timedelta(days=JWT_EXPIRATION_DAYS)
    )
    to_encode.update({"exp": expire, "iat": datetime.datetime.now(datetime.timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Verify and decode a signed JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


def get_current_user_from_request(request: Request) -> Optional[dict]:
    """Extract authenticated user payload from HttpOnly cookie or Authorization header."""
    token = request.cookies.get(JWT_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    if not token:
        return None
    return decode_access_token(token)


def set_auth_cookie(response: Response, token: str):
    """Set the HttpOnly, secure JWT cookie in the HTTP response."""
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * JWT_EXPIRATION_DAYS,
        expires=60 * 60 * 24 * JWT_EXPIRATION_DAYS,
        samesite="lax",
        secure=False,  # Set to True for HTTPS in production
        path="/"
    )


def clear_auth_cookie(response: Response):
    """Delete the JWT authentication cookie on logout."""
    response.delete_cookie(
        key=JWT_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax"
    )


def require_auth(request: Request) -> dict:
    """Ensure user is logged in, or redirect to login page."""
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_role(min_role: str = "student", allowed_roles: Optional[List[str]] = None):
    """
    Enforce role hierarchy:
    - min_role="teacher" allows "teacher" and "hod"
    - min_role="hod" allows only "hod"
    - allowed_roles allows explicit whitelisted roles
    """
    def role_dependency(request: Request) -> dict:
        user = get_current_user_from_request(request)
        if not user:
            raise HTTPException(status_code=303, headers={"Location": "/login"})

        user_role = user.get("role", "student")

        if allowed_roles:
            if user_role not in allowed_roles:
                if user_role == "student":
                    raise HTTPException(status_code=303, headers={"Location": "/student/dashboard"})
                raise HTTPException(status_code=403, detail=f"Unauthorized: Requires one of {allowed_roles}")
            return user

        user_level = ROLE_LEVELS.get(user_role, 1)
        required_level = ROLE_LEVELS.get(min_role, 1)

        if user_level < required_level:
            if user_role == "student":
                raise HTTPException(status_code=303, headers={"Location": "/student/dashboard"})
            raise HTTPException(status_code=403, detail="Insufficient permission level")

        return user
    return role_dependency
