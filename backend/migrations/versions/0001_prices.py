from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_prices",
        sa.Column("model_id", sa.String(255), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("family", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("input_cost_per_token", sa.Numeric(24, 16), nullable=False),
        sa.Column("output_cost_per_token", sa.Numeric(24, 16), nullable=False),
        sa.Column("cache_read_cost_per_token", sa.Numeric(24, 16), nullable=False),
        sa.Column("cache_write_cost_per_token", sa.Numeric(24, 16), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_model_prices_family", "model_prices", ["family"])
    op.create_table(
        "price_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("stored_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("price_sync_runs")
    op.drop_index("ix_model_prices_family", table_name="model_prices")
    op.drop_table("model_prices")
