"""Initial schema for Website & Advertisement Optimizer.

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create all initial tables, constraints, and indexes."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    op.create_table(
        "visitor_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visitor_id", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visitor_sessions_id", "visitor_sessions", ["id"], unique=False)
    op.create_index("ix_visitor_sessions_visitor_id", "visitor_sessions", ["visitor_id"], unique=False)

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("target_page", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_campaigns_id", "campaigns", ["id"], unique=False)
    op.create_index("ix_campaigns_status", "campaigns", ["status"], unique=False)
    op.create_index("ix_campaigns_target_page", "campaigns", ["target_page"], unique=False)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("page", sa.String(length=255), nullable=False),
        sa.Column("element", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["visitor_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_id", "events", ["id"], unique=False)
    op.create_index("ix_events_session_id", "events", ["session_id"], unique=False)
    op.create_index("ix_events_type", "events", ["type"], unique=False)

    op.create_table(
        "ads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("target_page", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ads_campaign_id", "ads", ["campaign_id"], unique=False)
    op.create_index("ix_ads_id", "ads", ["id"], unique=False)
    op.create_index("ix_ads_target_page", "ads", ["target_page"], unique=False)

    op.create_table(
        "impressions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ad_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clicked", sa.Boolean(), nullable=False),
        sa.Column("click_time", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ad_id"], ["ads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["visitor_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_impressions_ad_id", "impressions", ["ad_id"], unique=False)
    op.create_index("ix_impressions_id", "impressions", ["id"], unique=False)
    op.create_index("ix_impressions_session_id", "impressions", ["session_id"], unique=False)


def downgrade() -> None:
    """Drop all schema objects created by the initial migration."""
    op.drop_index("ix_impressions_session_id", table_name="impressions")
    op.drop_index("ix_impressions_id", table_name="impressions")
    op.drop_index("ix_impressions_ad_id", table_name="impressions")
    op.drop_table("impressions")

    op.drop_index("ix_ads_target_page", table_name="ads")
    op.drop_index("ix_ads_id", table_name="ads")
    op.drop_index("ix_ads_campaign_id", table_name="ads")
    op.drop_table("ads")

    op.drop_index("ix_events_type", table_name="events")
    op.drop_index("ix_events_session_id", table_name="events")
    op.drop_index("ix_events_id", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_campaigns_target_page", table_name="campaigns")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_id", table_name="campaigns")
    op.drop_table("campaigns")

    op.drop_index("ix_visitor_sessions_visitor_id", table_name="visitor_sessions")
    op.drop_index("ix_visitor_sessions_id", table_name="visitor_sessions")
    op.drop_table("visitor_sessions")

    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

