from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class RelationType(str, Enum):
    EXCLUSIVE = "exclusive"
    IMPLIES = "implies"
    IMPLIED_BY = "implied_by"
    SUBSET = "subset"
    SUPERSET = "superset"
    NEGATIVE_CORRELATION = "negative_correlation"
    POSITIVE_CORRELATION = "positive_correlation"
    OVERLAP = "overlap"
    UNRELATED = "unrelated"
    AMBIGUOUS = "ambiguous"


class OpportunityType(str, Enum):
    HARD_ARB = "hard_arb"
    STRUCTURAL_MISPRICING = "structural_mispricing"
    SOFT_DISLOCATION = "soft_dislocation"


class MarketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    title: str
    description: str | None
    rules: str | None
    category: str | None
    end_date: datetime | None
    active: bool
    outcomes_json: list | dict | None
    prices_json: list | dict | None
    volume: float | None
    liquidity: float | None
    raw_payload: dict
    fetched_at: datetime


class RelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    market_a_id: int
    market_b_id: int
    relation_type: RelationType
    relation_strength: float
    confidence: float
    reasoning_summary: str
    detected_by: str


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relation_id: int
    opportunity_type: OpportunityType
    score: float
    headline: str
    summary: str
    trade_idea: str
    risk_notes: str
    active: bool


class OpportunityListItem(BaseModel):
    opportunity: OpportunityRead
    relation: RelationRead
    market_a: MarketRead
    market_b: MarketRead


class OpportunityDetail(BaseModel):
    opportunity: OpportunityRead
    relation: RelationRead
    market_a: MarketRead
    market_b: MarketRead


class RefreshResponse(BaseModel):
    markets_fetched: int
    active_markets: int
    candidate_pairs: int
    relations_upserted: int
    opportunities_upserted: int

