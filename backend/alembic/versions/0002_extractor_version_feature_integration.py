"""extractor version on measurements; score-free feature-integration records

Additive only. Existing measurements keep extractor_version = NULL ("not recorded") — no value is
back-filled, because it was not recorded at the time. combined_results gains columns for
provenance-tagged feature records and allows indicator_level to be NULL (no score or label).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODES_OLD = "mode IN ('experimental_heuristic', 'trained_model')"
MODES_NEW = "mode IN ('experimental_heuristic', 'trained_model', 'feature_integration')"
STATUS_CHECK = "processing_status IS NULL OR processing_status IN ('complete', 'partial')"
MEASUREMENT_TABLES = ("facial_measurements", "motion_measurements", "voice_measurements")


def upgrade() -> None:
    for table in MEASUREMENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("extractor_version", sa.String(length=64), nullable=True))

    with op.batch_alter_table("combined_results") as batch:
        batch.add_column(sa.Column("processing_status", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("feature_schema_version", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("extractor_version", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("features", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("source_measurements", sa.JSON(), nullable=True))
        batch.alter_column("indicator_level", existing_type=sa.String(length=20), nullable=True)
        batch.drop_constraint(batch.f("ck_combined_results_mode"), type_="check")
        batch.create_check_constraint(batch.f("ck_combined_results_mode"), MODES_NEW)
        batch.create_check_constraint(batch.f("ck_combined_results_processing_status"), STATUS_CHECK)


UNSUPPORTED_UNDER_0001 = "mode = 'feature_integration' OR indicator_level IS NULL"


def downgrade() -> None:
    # Feature-integration records cannot exist under the 0001 schema (NULL indicator_level), so a
    # downgrade must delete them. Refuse unless the operator explicitly accepts that data loss.
    doomed = op.get_bind().execute(
        sa.text(f"SELECT COUNT(*) FROM combined_results WHERE {UNSUPPORTED_UNDER_0001}")
    ).scalar_one()
    allow = context.get_x_argument(as_dictionary=True).get("allow_data_loss", "").lower() == "true"
    if doomed and not allow:
        raise RuntimeError(
            f"Downgrade to 0001 would delete {doomed} saved combined record(s); nothing was changed. "
            "Back up first (python -m scripts.backup_db), then rerun with: "
            "alembic -x allow_data_loss=true downgrade 0001"
        )
    op.execute(f"DELETE FROM combined_results WHERE {UNSUPPORTED_UNDER_0001}")
    with op.batch_alter_table("combined_results") as batch:
        batch.drop_constraint(batch.f("ck_combined_results_processing_status"), type_="check")
        batch.drop_constraint(batch.f("ck_combined_results_mode"), type_="check")
        batch.create_check_constraint(batch.f("ck_combined_results_mode"), MODES_OLD)
        batch.alter_column("indicator_level", existing_type=sa.String(length=20), nullable=False)
        batch.drop_column("source_measurements")
        batch.drop_column("features")
        batch.drop_column("extractor_version")
        batch.drop_column("feature_schema_version")
        batch.drop_column("processing_status")

    for table in MEASUREMENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("extractor_version")
