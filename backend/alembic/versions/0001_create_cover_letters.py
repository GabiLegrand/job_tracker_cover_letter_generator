"""create cover_letters table

Revision ID: 0001
Revises:
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cover_letters",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("job_title", sa.String(), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("letter_content", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_cover_letters_company_jobtitle",
        "cover_letters",
        ["company_name", "job_title"],
    )


def downgrade() -> None:
    op.drop_index("ix_cover_letters_company_jobtitle", table_name="cover_letters")
    op.drop_table("cover_letters")
