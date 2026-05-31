"""Add visits table with doctor label fields.

Strategy: keep existing predictions table unchanged (backward compat).
New predictions are written to visits. Old predictions remain in predictions.

Revision ID: 001
Revises:
Create Date: 2026-05-31
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visits",
        sa.Column("id",               sa.Integer(),    primary_key=True),
        sa.Column("patient_id",       sa.String(64),   sa.ForeignKey("patients.patient_id",
                                      ondelete="SET NULL"), nullable=True),
        sa.Column("visit_date",       sa.DateTime(),   nullable=True),
        sa.Column("gestational_week", sa.Integer(),    nullable=True),
        sa.Column("screening_type",   sa.String(20),   nullable=True),
        sa.Column("input_format",     sa.String(30),   nullable=True),
        sa.Column("raw_input_ref",    sa.String(255),  nullable=True),
        sa.Column("predicted_class",  sa.String(20),   nullable=False),
        sa.Column("class_id",         sa.Integer(),    nullable=False),
        sa.Column("probabilities",    sa.JSON(),       nullable=True),
        sa.Column("features",         sa.JSON(),       nullable=True),
        sa.Column("shap_top",         sa.JSON(),       nullable=True),
        sa.Column("maternal_risk",    sa.JSON(),       nullable=True),
        sa.Column("model_version",    sa.String(50),   nullable=True),
        sa.Column("inference_ms",     sa.Float(),      nullable=True),
        sa.Column("warning",          sa.Text(),       nullable=True),
        sa.Column("doctor_label",     sa.String(1),    nullable=True),
        sa.Column("doctor_comment",   sa.Text(),       nullable=True),
        sa.Column("labeled_at",       sa.DateTime(),   nullable=True),
        sa.Column("created_at",       sa.DateTime(),   nullable=True),
    )
    op.create_index("ix_visits_patient_id", "visits", ["patient_id"])
    op.create_index("ix_visits_visit_date",  "visits", ["visit_date"])
    op.create_index("ix_visits_created_at",  "visits", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_visits_created_at",  table_name="visits")
    op.drop_index("ix_visits_visit_date",  table_name="visits")
    op.drop_index("ix_visits_patient_id",  table_name="visits")
    op.drop_table("visits")
