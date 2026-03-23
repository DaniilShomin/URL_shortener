"""create short_urls table

Revision ID: 20260323_000001
Revises: 
Create Date: 2026-03-23 00:00:01

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260323_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "short_urls",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("short_id", sa.String(length=12), nullable=False),
        sa.Column("original_url", sa.String(length=2048), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_short_urls_short_id"), "short_urls", ["short_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_short_urls_short_id"), table_name="short_urls")
    op.drop_table("short_urls")
