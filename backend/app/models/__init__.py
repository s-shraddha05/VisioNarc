"""Importing this package registers every table on Base.metadata (used by Alembic)."""

from app.models.admin import Admin, AdminSession
from app.models.analysis import (
    AnalysisSession,
    CombinedResult,
    ConsentRecord,
    FacialMeasurement,
    MotionMeasurement,
    VoiceMeasurement,
)
from app.models.audit import AuditLog
from app.models.model_version import ModelVersion
from app.models.screening import ScreeningResult
from app.models.setting import AppSetting

__all__ = [
    "Admin",
    "AdminSession",
    "AnalysisSession",
    "AppSetting",
    "AuditLog",
    "CombinedResult",
    "ConsentRecord",
    "FacialMeasurement",
    "ModelVersion",
    "MotionMeasurement",
    "ScreeningResult",
    "VoiceMeasurement",
]
