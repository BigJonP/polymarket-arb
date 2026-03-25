from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    outcomes_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    prices_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    relations_as_a: Mapped[list[Relation]] = relationship(
        back_populates="market_a",
        foreign_keys="Relation.market_a_id",
        cascade="all, delete-orphan",
    )
    relations_as_b: Mapped[list[Relation]] = relationship(
        back_populates="market_b",
        foreign_keys="Relation.market_b_id",
        cascade="all, delete-orphan",
    )


class Relation(Base):
    __tablename__ = "relations"
    __table_args__ = (UniqueConstraint("market_a_id", "market_b_id", name="uq_relation_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market_a_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True)
    market_b_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(64), index=True)
    relation_strength: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    reasoning_summary: Mapped[str] = mapped_column(Text)
    detected_by: Mapped[str] = mapped_column(String(32))

    market_a: Mapped[Market] = relationship(back_populates="relations_as_a", foreign_keys=[market_a_id])
    market_b: Mapped[Market] = relationship(back_populates="relations_as_b", foreign_keys=[market_b_id])
    opportunity: Mapped[Opportunity | None] = relationship(
        back_populates="relation",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    relation_id: Mapped[int] = mapped_column(ForeignKey("relations.id", ondelete="CASCADE"), unique=True, index=True)
    opportunity_type: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[float] = mapped_column(Float, index=True)
    headline: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text)
    trade_idea: Mapped[str] = mapped_column(Text)
    risk_notes: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    relation: Mapped[Relation] = relationship(back_populates="opportunity")

