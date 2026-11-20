"""screening results table; synthetic-session flag

Additive only: existing rows are untouched and every existing session gets is_synthetic = 0.
screening_results stores experimental screening outputs separately from measurements and
combined records. Only the synthetic demonstration writes to it (see app/analysis/screening.py).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODEL_STATUS_CHECK = (
    "model_status IN ('synthetic_demo', 'experimental', 'validated', 'unavailable', 'insufficient_input')"
)


def upgrade() -> None:
    with op.batch_alter_table("analysis_sessions") as batch:
        batch.add_column(sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("0"), nullable=False))

    op.create_table(
        "screening_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("combined_result_id", sa.Integer(), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("model_status", sa.String(length=24), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("target_definition", sa.Text(), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=16), nullable=True),
        sa.Column("input_measurement_ids", sa.JSON(), nullable=False),
        sa.Column("modality_status", sa.JSON(), nullable=False),
        sa.Column("missing_modalities", sa.JSON(), nullable=False),
        sa.Column("coverage", sa.Double(), nullable=True),
        sa.Column("estimate", sa.Double(), nullable=True),
        sa.Column("classification", sa.String(length=32), nullable=True),
        sa.Column("decision_threshold", sa.Double(), nullable=True),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(MODEL_STATUS_CHECK, name=op.f("ck_screening_results_model_status")),
        sa.CheckConstraint("estimate IS NULL OR (estimate >= 0 AND estimate <= 1)", name=op.f("ck_screening_results_estimate")),
        sa.CheckConstraint("coverage IS NULL OR (coverage >= 0 AND coverage <= 1)", name=op.f("ck_screening_results_coverage")),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"],
                                name=op.f("fk_screening_results_session_id_analysis_sessions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["combined_result_id"], ["combined_results.id"],
                                name=op.f("fk_screening_results_combined_result_id_combined_results"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"],
                                name=op.f("fk_screening_results_created_by_admin_id_admins"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_screening_results")),
    )
    op.create_index(op.f("ix_screening_results_session_id"), "screening_results", ["session_id"])
    op.create_index(op.f("ix_screening_results_combined_result_id"), "screening_results", ["combined_result_id"])


def downgrade() -> None:
    # Without is_synthetic, synthetic demo sessions would look like real ones, so they cannot be
    # kept. Refuse unless the operator explicitly accepts deleting them and all screening results.
    bind = op.get_bind()
    synthetic = bind.execute(sa.text("SELECT COUNT(*) FROM analysis_sessions WHERE is_synthetic = 1")).scalar_one()
    results = bind.execute(sa.text("SELECT COUNT(*) FROM screening_results")).scalar_one()
    allow = context.get_x_argument(as_dictionary=True).get("allow_data_loss", "").lower() == "true"
    if (synthetic or results) and not allow:
        raise RuntimeError(
            f"Downgrade to 0002 would delete {results} screening result(s) and {synthetic} synthetic demo "
            "session(s); nothing was changed. Back up first (python -m scripts.backup_db), then rerun with: "
            "alembic -x allow_data_loss=true downgrade 0002"
        )
    # Dropping the table drops its indexes; MySQL refuses to drop an index a foreign key still uses.
    op.drop_table("screening_results")

    # Child rows go with them (ON DELETE CASCADE).
    op.execute("DELETE FROM analysis_sessions WHERE is_synthetic = 1")
    with op.batch_alter_table("analysis_sessions") as batch:
        batch.drop_column("is_synthetic")
