from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Admin, AdminSession

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_session(
    db: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AdminSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        payload = decode_access_token(credentials.credentials, settings)
        admin_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise _unauthorized("Invalid or expired token") from None

    session = db.scalar(select(AdminSession).where(AdminSession.jti == payload["jti"]))
    if (
        session is None
        or session.admin_id != admin_id
        or session.revoked_at is not None
        or session.expires_at <= utcnow()
        or not session.admin.is_active
    ):
        raise _unauthorized("Session expired or signed out")
    return session


CurrentSession = Annotated[AdminSession, Depends(get_current_session)]


def get_current_admin(session: CurrentSession) -> Admin:
    return session.admin


CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
