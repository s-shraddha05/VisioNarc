from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import AppSettings, CurrentAdmin
from app.schemas.sessions import CONSENT_TEXT_VERSION

router = APIRouter(prefix="/settings", tags=["settings"])


class Capabilities(BaseModel):
    """Which analysis features the server can actually run. The UI disables everything else."""

    face_analysis: bool
    motion_analysis: bool
    voice_analysis: bool
    multimodal_analysis: bool
    pdf_reports: bool


class SettingsOut(BaseModel):
    environment: str
    store_raw_media: bool
    data_retention_days: int
    retention_enforcement: bool
    access_token_expire_minutes: int
    login_max_failed_attempts: int
    login_lockout_minutes: int
    consent_text_version: str
    capabilities: Capabilities


def _numpy_available() -> bool:
    try:
        import numpy  # noqa: F401
    except ImportError:
        return False
    return True


def _reportlab_available() -> bool:
    try:
        import reportlab  # noqa: F401
    except ImportError:
        return False
    return True


# Face/motion landmark detection runs in the browser; the server computes measurements with NumPy.
_NUMPY = _numpy_available()
CAPABILITIES = Capabilities(
    face_analysis=_NUMPY,
    motion_analysis=_NUMPY,
    voice_analysis=_NUMPY,
    multimodal_analysis=_NUMPY,  # side-by-side summary only; never a score
    pdf_reports=_reportlab_available(),
)


@router.get("", response_model=SettingsOut)
def get_settings_view(settings: AppSettings, _admin: CurrentAdmin):
    """Effective server configuration. Read-only: values come from backend/.env."""
    return SettingsOut(
        environment=settings.app_env,
        store_raw_media=settings.store_raw_media,
        data_retention_days=settings.data_retention_days,
        retention_enforcement=settings.retention_auto_purge,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        login_max_failed_attempts=settings.login_max_failed_attempts,
        login_lockout_minutes=settings.login_lockout_minutes,
        consent_text_version=CONSENT_TEXT_VERSION,
        capabilities=CAPABILITIES,
    )
