"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_workspaces_user_id", "workspaces", ["user_id"])

    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("workspaces.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("row_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("column_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("file_hash", sa.String(128)),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_datasets_workspace_id", "datasets", ["workspace_id"])
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])

    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("workspaces.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("layout_config", sa.JSON),
        sa.Column("is_default", sa.Boolean, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_dashboards_dataset_id", "dashboards", ["dataset_id"])

    op.create_table(
        "widgets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dashboard_id", sa.Integer, sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chart_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("config", sa.JSON),
        sa.Column("data_mapping", sa.JSON),
        sa.Column("position", sa.JSON),
        sa.Column("size", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_widgets_dashboard_id", "widgets", ["dashboard_id"])

    op.create_table(
        "forecast_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_type", sa.String(64), nullable=False),
        sa.Column("target_column", sa.String(255), nullable=False),
        sa.Column("date_column", sa.String(255), nullable=False),
        sa.Column("horizon", sa.Integer, nullable=False),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("metrics", sa.JSON),
        sa.Column("predictions", sa.JSON),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_forecast_runs_dataset_id", "forecast_runs", ["dataset_id"])

    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("baseline_metrics", sa.JSON),
        sa.Column("assumptions", sa.JSON),
        sa.Column("adjustments", sa.JSON),
        sa.Column("results", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_scenarios_dataset_id", "scenarios", ["dataset_id"])


def downgrade() -> None:
    op.drop_table("scenarios")
    op.drop_table("forecast_runs")
    op.drop_table("widgets")
    op.drop_table("dashboards")
    op.drop_table("datasets")
    op.drop_table("workspaces")
    op.drop_table("users")
Setup commands
powershell
cd Analyticx-AI\backend
.\.venv\Scripts\Activate.ps1
# If you already have analyticx.db, delete it once, then:
Remove-Item .\analyticx.db -ErrorAction SilentlyContinue
alembic upgrade head
After this, Base.metadata.create_all in main.py is still safe — Alembic tracks migrations. To fully rely on Alembic, remove the create_all call later.
