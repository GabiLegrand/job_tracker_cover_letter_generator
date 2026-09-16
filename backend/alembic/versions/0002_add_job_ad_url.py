"""add job_ad_url column to cover_letters

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cover_letters",
        sa.Column("job_ad_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cover_letters", "job_ad_url")
