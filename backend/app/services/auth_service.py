from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    burn_password_check,
    create_access_token,
    hash_password,
    normalize_username,
    validate_password_strength,
    validate_username,
    verify_password,
)
from app.db.base import utcnow
from app.models import Admin, AdminSession
from app.services import audit

# Same message for unknown user, wrong password, disabled or locked account,
# so the login form never reveals which usernames exist.
INVALID_CREDENTIALS = "Invalid username or password, or the account is temporarily locked."


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str | list[str]):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def login(
    db: Session,
    settings: Settings,
    username: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[Admin, str, datetime]:
    username = normalize_username(username)
    admin = db.scalar(select(Admin).where(Admin.username == username))
    now = utcnow()

    def fail(reason: str, admin_id: int | None = None) -> AuthError:
        audit.record(
            db,
            "auth.login_failed",
            admin_id=admin_id,
            details={"username": username[:50], "reason": reason},
            ip_address=ip_address,
        )
        db.commit()
        return AuthError(401, INVALID_CREDENTIALS)

    if admin is None:
        burn_password_check(password, settings.bcrypt_rounds)
        raise fail("unknown_user")
    if not admin.is_active:
        burn_password_check(password, settings.bcrypt_rounds)
        raise fail("inactive", admin.id)
    if admin.locked_until and admin.locked_until > now:
        burn_password_check(password, settings.bcrypt_rounds)
        raise fail("locked", admin.id)

    if not verify_password(password, admin.password_hash):
        admin.failed_login_attempts += 1
        if admin.failed_login_attempts >= settings.login_max_failed_attempts:
            admin.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            admin.failed_login_attempts = 0
            audit.record(
                db,
                "auth.account_locked",
                admin_id=admin.id,
                details={"minutes": settings.login_lockout_minutes},
                ip_address=ip_address,
            )
        raise fail("wrong_password", admin.id)

    admin.failed_login_attempts = 0
    admin.locked_until = None
    admin.last_login_at = now
    token, jti, expires_at = create_access_token(admin.id, settings)
    db.add(
        AdminSession(
            admin_id=admin.id,
            jti=jti,
            issued_at=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    audit.record(db, "auth.login", admin_id=admin.id, ip_address=ip_address)
    db.commit()
    return admin, token, expires_at


def logout(db: Session, session: AdminSession, ip_address: str | None) -> None:
    session.revoked_at = utcnow()
    audit.record(db, "auth.logout", admin_id=session.admin_id, ip_address=ip_address)
    db.commit()


def revoke_all_sessions(db: Session, admin_id: int, except_jti: str | None = None) -> None:
    stmt = (
        update(AdminSession)
        .where(AdminSession.admin_id == admin_id, AdminSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    if except_jti:
        stmt = stmt.where(AdminSession.jti != except_jti)
    db.execute(stmt)


def change_password(
    db: Session,
    settings: Settings,
    session: AdminSession,
    current_password: str,
    new_password: str,
    ip_address: str | None,
) -> None:
    admin = session.admin
    if not verify_password(current_password, admin.password_hash):
        audit.record(db, "auth.password_change_failed", admin_id=admin.id, ip_address=ip_address)
        db.commit()
        raise AuthError(400, "Current password is incorrect.")
    errors = validate_password_strength(new_password)
    if new_password == current_password:
        errors.append("New password must be different from the current password.")
    if errors:
        raise AuthError(422, errors)

    set_password(db, settings, admin, new_password)
    # Keep the session that made the change; sign out every other device.
    revoke_all_sessions(db, admin.id, except_jti=session.jti)
    audit.record(db, "auth.password_changed", admin_id=admin.id, ip_address=ip_address)
    db.commit()


def set_password(db: Session, settings: Settings, admin: Admin, new_password: str) -> None:
    admin.password_hash = hash_password(new_password, settings.bcrypt_rounds)
    admin.password_changed_at = utcnow()
    admin.failed_login_attempts = 0
    admin.locked_until = None


def create_admin(
    db: Session, settings: Settings, username: str, password: str, full_name: str | None
) -> Admin:
    username = normalize_username(username)
    errors = validate_username(username) + validate_password_strength(password)
    if db.scalar(select(Admin.id).where(Admin.username == username)) is not None:
        errors.append(f"An administrator named '{username}' already exists.")
    if errors:
        raise AuthError(422, errors)
    admin = Admin(
        username=username,
        password_hash=hash_password(password, settings.bcrypt_rounds),
        full_name=(full_name or "").strip() or None,
    )
    db.add(admin)
    db.flush()
    audit.record(db, "admin.created", admin_id=admin.id, entity_type="admin", entity_id=admin.id)
    db.commit()
    return admin
