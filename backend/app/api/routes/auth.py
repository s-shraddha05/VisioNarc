from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update

from app.db.base import utcnow
from app.models import AdminSession
from app.schemas.common import UTCDateTime

from app.api.deps import AppSettings, CurrentAdmin, CurrentSession, DbSession, client_ip
from app.schemas.auth import (
    AdminOut,
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    ProfileUpdate,
    TokenResponse,
)
from app.services import audit, auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: DbSession, settings: AppSettings):
    ip = client_ip(request)  # TCP peer address; forwarded headers are deliberately ignored
    limiter = request.app.state.login_limiter
    key = ip or "unknown"
    wait = limiter.retry_after(key)
    if wait is not None:
        audit.record(db, "auth.login_rate_limited", details={"retry_after_s": wait}, ip_address=ip)
        db.commit()
        raise HTTPException(
            429,
            "Too many failed sign-in attempts from this computer. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    try:
        admin, token, expires_at = auth_service.login(
            db,
            settings,
            body.username,
            body.password,
            ip,
            request.headers.get("user-agent"),
        )
    except AuthError as exc:
        if exc.status_code == 401:
            limiter.record_failure(key)
        raise HTTPException(exc.status_code, exc.detail) from None
    return TokenResponse(
        access_token=token, expires_at=expires_at, admin=AdminOut.model_validate(admin)
    )


@router.post("/logout", response_model=MessageResponse)
def logout(session: CurrentSession, request: Request, db: DbSession):
    auth_service.logout(db, session, client_ip(request))
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=AdminOut)
def me(admin: CurrentAdmin):
    return admin


@router.patch("/me", response_model=AdminOut)
def update_profile(body: ProfileUpdate, admin: CurrentAdmin, request: Request, db: DbSession):
    admin.full_name = " ".join((body.full_name or "").split()) or None
    audit.record(db, "admin.profile_updated", admin_id=admin.id, ip_address=client_ip(request))
    db.commit()
    return admin


class AdminSessionOut(BaseModel):
    id: int
    issued_at: UTCDateTime
    expires_at: UTCDateTime
    ip_address: str | None
    user_agent: str | None
    current: bool


@router.get("/sessions", response_model=list[AdminSessionOut])
def list_sessions(session: CurrentSession, db: DbSession):
    """The current administrator's active (not revoked, not expired) sign-ins."""
    rows = db.scalars(
        select(AdminSession)
        .where(
            AdminSession.admin_id == session.admin_id,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > utcnow(),
        )
        .order_by(AdminSession.issued_at.desc(), AdminSession.id.desc())
    ).all()
    return [
        AdminSessionOut(id=r.id, issued_at=r.issued_at, expires_at=r.expires_at, ip_address=r.ip_address,
                        user_agent=r.user_agent, current=r.id == session.id)
        for r in rows
    ]


@router.post("/sessions/{session_id}/revoke", response_model=MessageResponse)
def revoke_session(session_id: int, session: CurrentSession, request: Request, db: DbSession):
    target = db.get(AdminSession, session_id)
    # Only your own, still-active sign-ins; anything else looks like "not found".
    if target is None or target.admin_id != session.admin_id or target.revoked_at is not None:
        raise HTTPException(404, "Active sign-in not found.")
    target.revoked_at = utcnow()
    audit.record(db, "auth.session_revoked", admin_id=session.admin_id,
                 details={"admin_session_id": session_id, "current": session_id == session.id},
                 ip_address=client_ip(request))
    db.commit()
    return MessageResponse(message="Signed out." if session_id == session.id else "That sign-in was revoked.")


@router.post("/sessions/revoke-others", response_model=MessageResponse)
def revoke_other_sessions(session: CurrentSession, request: Request, db: DbSession):
    result = db.execute(
        update(AdminSession)
        .where(AdminSession.admin_id == session.admin_id, AdminSession.revoked_at.is_(None),
               AdminSession.id != session.id)
        .values(revoked_at=utcnow())
    )
    audit.record(db, "auth.sessions_revoked_others", admin_id=session.admin_id,
                 details={"count": result.rowcount}, ip_address=client_ip(request))
    db.commit()
    return MessageResponse(message=f"Signed out {result.rowcount} other sign-in(s).")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest,
    session: CurrentSession,
    request: Request,
    db: DbSession,
    settings: AppSettings,
):
    try:
        auth_service.change_password(
            db, settings, session, body.current_password, body.new_password, client_ip(request)
        )
    except AuthError as exc:
        raise HTTPException(exc.status_code, exc.detail) from None
    return MessageResponse(message="Password changed. Other sessions were signed out.")
