from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.constants import (
    EXCLUSIVE_HARD_ARB_CONFIDENCE_THRESHOLD,
    EXCLUSIVE_HARD_ARB_EXCESS_THRESHOLD,
    EXCLUSIVE_HARD_ARB_RELATION_STRENGTH_THRESHOLD,
    EXCLUSIVE_MIN_EXCESS_THRESHOLD,
    EXCLUSIVE_SCORE_CONFIDENCE_WEIGHT,
    EXCLUSIVE_SCORE_EXCESS_WEIGHT,
    EXCLUSIVE_SCORE_RELATION_STRENGTH_WEIGHT,
    IMPLICATION_HARD_ARB_CONFIDENCE_THRESHOLD,
    IMPLICATION_HARD_ARB_GAP_THRESHOLD,
    IMPLICATION_HARD_ARB_RELATION_STRENGTH_THRESHOLD,
    IMPLICATION_MIN_GAP_THRESHOLD,
    IMPLICATION_SCORE_CONFIDENCE_WEIGHT,
    IMPLICATION_SCORE_GAP_WEIGHT,
    IMPLICATION_SCORE_RELATION_STRENGTH_WEIGHT,
    NEGATIVE_CORRELATION_MIN_JOINT_RICHNESS_THRESHOLD,
    NEGATIVE_CORRELATION_SCORE_CONFIDENCE_WEIGHT,
    NEGATIVE_CORRELATION_SCORE_JOINT_RICHNESS_WEIGHT,
    NEGATIVE_CORRELATION_SCORE_RELATION_STRENGTH_WEIGHT,
    POSITIVE_CORRELATION_MIN_DIVERGENCE_THRESHOLD,
    POSITIVE_CORRELATION_SCORE_CONFIDENCE_WEIGHT,
    POSITIVE_CORRELATION_SCORE_DIVERGENCE_WEIGHT,
    POSITIVE_CORRELATION_SCORE_RELATION_STRENGTH_WEIGHT,
)
from app.models import Market, Relation
from app.schemas import OpportunityType, RelationType


@dataclass(frozen=True)
class OpportunityPayload:
    opportunity_type: OpportunityType
    score: float
    headline: str
    summary: str
    trade_idea: str
    risk_notes: str


class OpportunityScorer:
    def score(self, relation: Relation, market_a: Market, market_b: Market) -> OpportunityPayload | None:
        probability_a = self._extract_probability(market_a)
        probability_b = self._extract_probability(market_b)
        if probability_a is None or probability_b is None:
            return None

        relation_type = RelationType(relation.relation_type)
        if relation_type == RelationType.EXCLUSIVE:
            return self._score_exclusive(relation, market_a, market_b, probability_a, probability_b)
        if relation_type in {RelationType.IMPLIES, RelationType.SUBSET}:
            return self._score_implies(relation, market_a, market_b, probability_a, probability_b)
        if relation_type in {RelationType.IMPLIED_BY, RelationType.SUPERSET}:
            return self._score_implied_by(relation, market_a, market_b, probability_a, probability_b)
        if relation_type == RelationType.NEGATIVE_CORRELATION:
            return self._score_negative_correlation(relation, market_a, market_b, probability_a, probability_b)
        if relation_type == RelationType.POSITIVE_CORRELATION:
            return self._score_positive_correlation(relation, market_a, market_b, probability_a, probability_b)
        return None

    def _score_exclusive(
        self,
        relation: Relation,
        market_a: Market,
        market_b: Market,
        probability_a: float,
        probability_b: float,
    ) -> OpportunityPayload | None:
        excess = probability_a + probability_b - 1.0
        if excess < EXCLUSIVE_MIN_EXCESS_THRESHOLD:
            return None

        opportunity_type = (
            OpportunityType.HARD_ARB
            if (
                self._hard_arb_allowed(relation)
                and excess >= EXCLUSIVE_HARD_ARB_EXCESS_THRESHOLD
                and relation.confidence >= EXCLUSIVE_HARD_ARB_CONFIDENCE_THRESHOLD
                and relation.relation_strength >= EXCLUSIVE_HARD_ARB_RELATION_STRENGTH_THRESHOLD
            )
            else OpportunityType.STRUCTURAL_MISPRICING
        )
        score = self._bounded_score(
            excess * EXCLUSIVE_SCORE_EXCESS_WEIGHT
            + relation.confidence * EXCLUSIVE_SCORE_CONFIDENCE_WEIGHT
            + relation.relation_strength * EXCLUSIVE_SCORE_RELATION_STRENGTH_WEIGHT
        )
        headline = f"Exclusive markets price to {(probability_a + probability_b) * 100:.1f}%"
        summary = (
            f"Both markets are treated as mutually exclusive, yet {market_a.title} and {market_b.title} "
            f"sum to {(probability_a + probability_b) * 100:.1f}%."
        )
        trade_idea = (
            f"Fade the combined overpricing by selling or avoiding both legs, or by leaning against the richer of the two "
            f"prices if execution is available."
        )
        risk_notes = "This only behaves like hard arb if the exclusivity call is correct and both contracts resolve independently without hidden overlap."
        return OpportunityPayload(opportunity_type, score, headline, summary, trade_idea, risk_notes)

    def _score_implies(
        self,
        relation: Relation,
        market_a: Market,
        market_b: Market,
        probability_a: float,
        probability_b: float,
    ) -> OpportunityPayload | None:
        gap = probability_a - probability_b
        if gap < IMPLICATION_MIN_GAP_THRESHOLD:
            return None

        opportunity_type = (
            OpportunityType.HARD_ARB
            if (
                self._hard_arb_allowed(relation)
                and gap >= IMPLICATION_HARD_ARB_GAP_THRESHOLD
                and relation.confidence >= IMPLICATION_HARD_ARB_CONFIDENCE_THRESHOLD
                and relation.relation_strength >= IMPLICATION_HARD_ARB_RELATION_STRENGTH_THRESHOLD
            )
            else OpportunityType.STRUCTURAL_MISPRICING
        )
        score = self._bounded_score(
            gap * IMPLICATION_SCORE_GAP_WEIGHT
            + relation.confidence * IMPLICATION_SCORE_CONFIDENCE_WEIGHT
            + relation.relation_strength * IMPLICATION_SCORE_RELATION_STRENGTH_WEIGHT
        )
        headline = f"Implication chain inverted by {gap * 100:.1f} pts"
        summary = (
            f"If Market A resolves true, Market B should also resolve true. "
            f"Instead, A is priced at {probability_a * 100:.1f}% and B at {probability_b * 100:.1f}%."
        )
        trade_idea = f"Relative-value view: own or prefer Market B versus Market A until the implication ordering normalizes."
        risk_notes = "Watch for rule differences, timeline mismatches, or settlement edge cases that weaken the implication."
        return OpportunityPayload(opportunity_type, score, headline, summary, trade_idea, risk_notes)

    def _score_implied_by(
        self,
        relation: Relation,
        market_a: Market,
        market_b: Market,
        probability_a: float,
        probability_b: float,
    ) -> OpportunityPayload | None:
        gap = probability_b - probability_a
        if gap < IMPLICATION_MIN_GAP_THRESHOLD:
            return None

        opportunity_type = (
            OpportunityType.HARD_ARB
            if (
                self._hard_arb_allowed(relation)
                and gap >= IMPLICATION_HARD_ARB_GAP_THRESHOLD
                and relation.confidence >= IMPLICATION_HARD_ARB_CONFIDENCE_THRESHOLD
                and relation.relation_strength >= IMPLICATION_HARD_ARB_RELATION_STRENGTH_THRESHOLD
            )
            else OpportunityType.STRUCTURAL_MISPRICING
        )
        score = self._bounded_score(
            gap * IMPLICATION_SCORE_GAP_WEIGHT
            + relation.confidence * IMPLICATION_SCORE_CONFIDENCE_WEIGHT
            + relation.relation_strength * IMPLICATION_SCORE_RELATION_STRENGTH_WEIGHT
        )
        headline = f"Reverse implication mismatch of {gap * 100:.1f} pts"
        summary = (
            f"Market B appears to imply Market A, but B is priced at {probability_b * 100:.1f}% "
            f"while A is only {probability_a * 100:.1f}%."
        )
        trade_idea = f"Relative-value view: own or prefer Market A versus Market B if the implication is real."
        risk_notes = "This is only robust if the inferred direction really runs from Market B into Market A."
        return OpportunityPayload(opportunity_type, score, headline, summary, trade_idea, risk_notes)

    def _score_negative_correlation(
        self,
        relation: Relation,
        market_a: Market,
        market_b: Market,
        probability_a: float,
        probability_b: float,
    ) -> OpportunityPayload | None:
        joint_richness = probability_a + probability_b - 1.0
        if joint_richness < NEGATIVE_CORRELATION_MIN_JOINT_RICHNESS_THRESHOLD:
            return None

        score = self._bounded_score(
            joint_richness * NEGATIVE_CORRELATION_SCORE_JOINT_RICHNESS_WEIGHT
            + relation.confidence * NEGATIVE_CORRELATION_SCORE_CONFIDENCE_WEIGHT
            + relation.relation_strength * NEGATIVE_CORRELATION_SCORE_RELATION_STRENGTH_WEIGHT
        )
        headline = f"Negatively correlated pair looks jointly rich at {(probability_a + probability_b) * 100:.1f}%"
        summary = (
            f"The pair is not logically exclusive, but the model sees a negative relationship and both legs are priced high "
            f"simultaneously."
        )
        trade_idea = "Treat this as a soft dislocation: be cautious on both legs or lean toward the cheaper side of the relationship."
        risk_notes = "Correlation is not exclusivity. Both markets can still resolve true together unless the rules say otherwise."
        return OpportunityPayload(OpportunityType.SOFT_DISLOCATION, score, headline, summary, trade_idea, risk_notes)

    def _score_positive_correlation(
        self,
        relation: Relation,
        market_a: Market,
        market_b: Market,
        probability_a: float,
        probability_b: float,
    ) -> OpportunityPayload | None:
        divergence = abs(probability_a - probability_b)
        if divergence < POSITIVE_CORRELATION_MIN_DIVERGENCE_THRESHOLD:
            return None

        richer = market_a.title if probability_a > probability_b else market_b.title
        score = self._bounded_score(
            divergence * POSITIVE_CORRELATION_SCORE_DIVERGENCE_WEIGHT
            + relation.confidence * POSITIVE_CORRELATION_SCORE_CONFIDENCE_WEIGHT
            + relation.relation_strength * POSITIVE_CORRELATION_SCORE_RELATION_STRENGTH_WEIGHT
        )
        headline = f"Positively related markets diverge by {divergence * 100:.1f} pts"
        summary = f"The relation looks directionally aligned, but the market prices diverge much more than the link strength suggests."
        trade_idea = f"Treat {richer} as the richer leg and look for mean reversion rather than a hard hedge."
        risk_notes = "Positive correlation can break for long periods, especially when one contract has cleaner rules or deeper liquidity."
        return OpportunityPayload(OpportunityType.SOFT_DISLOCATION, score, headline, summary, trade_idea, risk_notes)

    def _extract_probability(self, market: Market) -> float | None:
        prices = market.prices_json
        outcomes = market.outcomes_json
        if isinstance(prices, dict):
            for key, value in prices.items():
                if str(key).lower() == "yes":
                    return self._to_probability(value)
            if prices:
                return self._to_probability(next(iter(prices.values())))
        if isinstance(prices, list):
            if isinstance(outcomes, list):
                for outcome, value in zip(outcomes, prices):
                    if str(outcome).strip().lower() == "yes":
                        return self._to_probability(value)
            if prices:
                return self._to_probability(prices[0])
        return None

    def _to_probability(self, value: Any) -> float | None:
        try:
            probability = float(value)
        except (TypeError, ValueError):
            return None
        if probability > 1:
            probability = probability / 100
        return max(0.0, min(1.0, probability))

    def _bounded_score(self, value: float) -> float:
        return round(max(0.0, min(100.0, value)), 1)

    def _hard_arb_allowed(self, relation: Relation) -> bool:
        return relation.detected_by in {"rule", "hybrid"}
