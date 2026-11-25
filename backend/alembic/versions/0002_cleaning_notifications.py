"""add transformations and notifications

Revision ID: 0002_cleaning_notifications
Revises: 0001_initial
Create Date: 2025-02-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_cleaning_notifications"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transformations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transformation_type", sa.String(64), nullable=False),
        sa.Column("parameters", sa.JSON),
        sa.Column("description", sa.Text),
        sa.Column("row_count_before", sa.Integer),
        sa.Column("row_count_after", sa.Integer),
        sa.Column("applied_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_transformations_dataset_id", "transformations", ["dataset_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("level", sa.String(32), server_default="info"),
        sa.Column("is_read", sa.Boolean, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("transformations")
