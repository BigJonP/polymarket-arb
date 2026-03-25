from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Market, Opportunity, Relation
from app.schemas import RefreshResponse
from app.services.candidate_generation import CandidateGenerator
from app.services.llm import build_llm_service
from app.services.opportunity_scoring import OpportunityScorer
from app.services.polymarket_client import NormalizedMarket, PolymarketClient
from app.services.relation_analysis import RelationAnalyzer


class RefreshPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.client = PolymarketClient()
        self.generator = CandidateGenerator()
        self.analyzer = RelationAnalyzer(build_llm_service())
        self.scorer = OpportunityScorer()

    def run(self) -> RefreshResponse:
        fetched_markets = self.client.fetch_active_markets()
        persisted_markets = self._upsert_markets(fetched_markets)

        scanned_markets = persisted_markets[: self.settings.market_scan_limit]
        candidate_pairs = self.generator.generate(scanned_markets)
        relation_results = self.analyzer.analyze_pairs(
            [(candidate.market_a, candidate.market_b) for candidate in candidate_pairs]
        )

        self.db.execute(update(Opportunity).values(active=False))
        relations_upserted = 0
        opportunities_upserted = 0

        for candidate, relation_result in zip(candidate_pairs, relation_results):
            relation = self._upsert_relation(candidate.market_a, candidate.market_b, relation_result)
            relations_upserted += 1

            opportunity_payload = self.scorer.score(relation, candidate.market_a, candidate.market_b)
            if opportunity_payload is None:
                if relation.opportunity is not None:
                    relation.opportunity.active = False
                continue

            self._upsert_opportunity(relation, opportunity_payload)
            opportunities_upserted += 1

        self.db.commit()
        return RefreshResponse(
            markets_fetched=len(fetched_markets),
            active_markets=len(scanned_markets),
            candidate_pairs=len(candidate_pairs),
            relations_upserted=relations_upserted,
            opportunities_upserted=opportunities_upserted,
        )

    def _upsert_markets(self, fetched_markets: list[NormalizedMarket]) -> list[Market]:
        external_ids = [market.external_id for market in fetched_markets]
        existing = {
            market.external_id: market
            for market in self.db.scalars(select(Market).where(Market.external_id.in_(external_ids))).all()
        }
        persisted_markets: list[Market] = []

        for fetched_market in fetched_markets:
            market = existing.get(fetched_market.external_id)
            if market is None:
                market = Market(external_id=fetched_market.external_id, raw_payload={})
                self.db.add(market)
            market.title = fetched_market.title
            market.description = fetched_market.description
            market.rules = fetched_market.rules
            market.category = fetched_market.category
            market.end_date = fetched_market.end_date
            market.active = fetched_market.active
            market.outcomes_json = fetched_market.outcomes_json
            market.prices_json = fetched_market.prices_json
            market.volume = fetched_market.volume
            market.liquidity = fetched_market.liquidity
            market.raw_payload = fetched_market.raw_payload
            market.fetched_at = fetched_market.fetched_at
            persisted_markets.append(market)

        if external_ids:
            self.db.execute(update(Market).where(Market.external_id.not_in(external_ids)).values(active=False))

        self.db.flush()
        return persisted_markets

    def _upsert_relation(self, market_a: Market, market_b: Market, result) -> Relation:
        relation = self.db.scalars(
            select(Relation).where(Relation.market_a_id == market_a.id, Relation.market_b_id == market_b.id)
        ).first()
        if relation is None:
            relation = Relation(market_a_id=market_a.id, market_b_id=market_b.id)
            self.db.add(relation)

        relation.relation_type = result.relation_type.value
        relation.relation_strength = result.relation_strength
        relation.confidence = result.confidence
        relation.reasoning_summary = result.reasoning_summary
        relation.detected_by = result.detected_by
        self.db.flush()
        return relation

    def _upsert_opportunity(self, relation: Relation, payload) -> None:
        opportunity = relation.opportunity
        if opportunity is None:
            opportunity = Opportunity(relation_id=relation.id)
            self.db.add(opportunity)

        opportunity.opportunity_type = payload.opportunity_type.value
        opportunity.score = payload.score
        opportunity.headline = payload.headline
        opportunity.summary = payload.summary
        opportunity.trade_idea = payload.trade_idea
        opportunity.risk_notes = payload.risk_notes
        opportunity.active = True
        self.db.flush()
