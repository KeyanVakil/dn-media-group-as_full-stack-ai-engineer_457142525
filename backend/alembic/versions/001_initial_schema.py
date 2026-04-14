"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.UUID(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.String(500), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("analyzed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_url"),
    )

    op.create_table(
        "article_summaries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("article_id", sa.UUID(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("topics", postgresql.JSONB(), server_default="[]"),
        sa.Column("key_facts", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id"),
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("article_count", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "type", name="uq_entity_name_type"),
    )

    op.create_table(
        "article_entities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("article_id", sa.UUID(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("entity_id", sa.UUID(), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("sentiment", sa.Float(), server_default="0.0"),
        sa.Column("relevance", sa.Float(), server_default="0.5"),
        sa.Column("context", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "entity_id", name="uq_article_entity"),
    )

    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_a_id", sa.UUID(), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("entity_b_id", sa.UUID(), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("relationship_type", sa.String(100), server_default="'co-occurrence'"),
        sa.Column("strength", sa.Float(), server_default="0.0"),
        sa.Column("evidence_count", sa.Integer(), server_default="1"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_a_id", "entity_b_id", name="uq_entity_relationship"),
        sa.CheckConstraint("entity_a_id < entity_b_id", name="ck_entity_ordering"),
    )

    op.create_table(
        "research_tasks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="'pending'"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "research_steps",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_id", sa.UUID(), sa.ForeignKey("research_tasks.id"), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("input_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("research_steps")
    op.drop_table("research_tasks")
    op.drop_table("entity_relationships")
    op.drop_table("article_entities")
    op.drop_table("entities")
    op.drop_table("article_summaries")
    op.drop_table("articles")
    op.drop_table("sources")
