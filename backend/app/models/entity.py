import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("name", "type", name="uq_entity_name_type"),)

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    article_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    article_entities: Mapped[list["ArticleEntity"]] = relationship(back_populates="entity")


class ArticleEntity(Base):
    __tablename__ = "article_entities"
    __table_args__ = (
        UniqueConstraint("article_id", "entity_id", name="uq_article_entity"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    sentiment: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    relevance: Mapped[float] = mapped_column(Float, default=0.5, server_default="0.5")
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    article: Mapped["Article"] = relationship(back_populates="article_entities")  # noqa: F821
    entity: Mapped["Entity"] = relationship(back_populates="article_entities")


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint("entity_a_id", "entity_b_id", name="uq_entity_relationship"),
        CheckConstraint("entity_a_id < entity_b_id", name="ck_entity_ordering"),
    )

    entity_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    entity_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100), default="co-occurrence", server_default="'co-occurrence'"
    )
    strength: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    evidence_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    entity_a: Mapped["Entity"] = relationship(foreign_keys=[entity_a_id])
    entity_b: Mapped["Entity"] = relationship(foreign_keys=[entity_b_id])
