from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations

from app.constants import (
    CANDIDATE_DATE_BUCKET_INDEX_MAX_BUCKET_SIZE,
    CANDIDATE_ENTITY_INDEX_MAX_BUCKET_SIZE,
    CANDIDATE_KEYWORD_INDEX_MAX_BUCKET_SIZE,
    CANDIDATE_MAX_PAIRS_PER_MARKET,
    CANDIDATE_MIN_KEYWORD_LENGTH,
    CANDIDATE_PAIR_SCORE_THRESHOLD,
    CANDIDATE_SAME_CATEGORY_BONUS,
    CANDIDATE_SAME_DATE_BUCKET_BONUS,
    CANDIDATE_SHARED_ENTITY_CAP,
    CANDIDATE_SHARED_ENTITY_WEIGHT,
    CANDIDATE_SHARED_KEYWORD_CAP,
    CANDIDATE_SHARED_KEYWORD_WEIGHT,
    CANDIDATE_TITLE_SIMILARITY_THRESHOLD,
    CANDIDATE_TITLE_SIMILARITY_WEIGHT,
)
from app.models import Market


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "what",
    "when",
    "who",
    "will",
    "with",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


@dataclass(frozen=True)
class CandidatePair:
    market_a: Market
    market_b: Market
    heuristic_score: float
    reasons: list[str]


@dataclass(frozen=True)
class MarketFeatures:
    keywords: set[str]
    entities: set[str]
    normalized_title: str
    category: str
    date_bucket: str | None


class CandidateGenerator:
    def generate(self, markets: list[Market]) -> list[CandidatePair]:
        if len(markets) < 2:
            return []

        by_id = {market.id: market for market in markets}
        features = {market.id: self._build_features(market) for market in markets}
        pair_ids: set[tuple[int, int]] = set()

        for index in (self._keyword_index(features), self._entity_index(features), self._date_bucket_index(features)):
            for market_ids in index.values():
                if len(market_ids) < 2:
                    continue
                for left_id, right_id in combinations(sorted(market_ids), 2):
                    pair_ids.add((left_id, right_id))

        scored_pairs: list[CandidatePair] = []
        market_pair_counts = defaultdict(int)
        for left_id, right_id in sorted(pair_ids):
            market_a = by_id[left_id]
            market_b = by_id[right_id]
            score, reasons = self._score_pair(market_a, market_b, features[left_id], features[right_id])
            if score < CANDIDATE_PAIR_SCORE_THRESHOLD:
                continue
            if (
                market_pair_counts[left_id] >= CANDIDATE_MAX_PAIRS_PER_MARKET
                or market_pair_counts[right_id] >= CANDIDATE_MAX_PAIRS_PER_MARKET
            ):
                continue
            scored_pairs.append(CandidatePair(market_a=market_a, market_b=market_b, heuristic_score=score, reasons=reasons))
            market_pair_counts[left_id] += 1
            market_pair_counts[right_id] += 1

        scored_pairs.sort(key=lambda pair: pair.heuristic_score, reverse=True)
        return scored_pairs

    def _build_features(self, market: Market) -> MarketFeatures:
        text = " ".join(part for part in [market.title, market.description or "", market.rules or ""] if part)
        keywords = {
            token
            for token in self._tokenize(text)
            if len(token) >= CANDIDATE_MIN_KEYWORD_LENGTH and token not in STOPWORDS
        }
        entities = {
            token
            for token in TOKEN_RE.findall(text)
            if (token[:1].isupper() and len(token) > 2) or token.isdigit() and len(token) == 4
        }
        return MarketFeatures(
            keywords=keywords,
            entities={entity.lower() for entity in entities},
            normalized_title=self._normalize_text(market.title),
            category=(market.category or "").strip().lower(),
            date_bucket=market.end_date.strftime("%Y-%m") if market.end_date else None,
        )

    def _keyword_index(self, features: dict[int, MarketFeatures]) -> dict[str, set[int]]:
        index: dict[str, set[int]] = defaultdict(set)
        for market_id, market_features in features.items():
            for token in market_features.keywords:
                index[token].add(market_id)
        return {
            token: market_ids
            for token, market_ids in index.items()
            if 1 < len(market_ids) <= CANDIDATE_KEYWORD_INDEX_MAX_BUCKET_SIZE
        }

    def _entity_index(self, features: dict[int, MarketFeatures]) -> dict[str, set[int]]:
        index: dict[str, set[int]] = defaultdict(set)
        for market_id, market_features in features.items():
            for token in market_features.entities:
                index[token].add(market_id)
        return {
            token: market_ids
            for token, market_ids in index.items()
            if 1 < len(market_ids) <= CANDIDATE_ENTITY_INDEX_MAX_BUCKET_SIZE
        }

    def _date_bucket_index(self, features: dict[int, MarketFeatures]) -> dict[str, set[int]]:
        index: dict[str, set[int]] = defaultdict(set)
        for market_id, market_features in features.items():
            if market_features.date_bucket:
                index[f"{market_features.category}:{market_features.date_bucket}"].add(market_id)
        return {
            bucket: market_ids
            for bucket, market_ids in index.items()
            if 1 < len(market_ids) <= CANDIDATE_DATE_BUCKET_INDEX_MAX_BUCKET_SIZE
        }

    def _score_pair(
        self,
        market_a: Market,
        market_b: Market,
        features_a: MarketFeatures,
        features_b: MarketFeatures,
    ) -> tuple[float, list[str]]:
        shared_keywords = features_a.keywords & features_b.keywords
        shared_entities = features_a.entities & features_b.entities
        title_similarity = SequenceMatcher(None, features_a.normalized_title, features_b.normalized_title).ratio()
        same_category = bool(features_a.category and features_a.category == features_b.category)
        same_date_bucket = bool(features_a.date_bucket and features_a.date_bucket == features_b.date_bucket)

        score = min(len(shared_keywords), CANDIDATE_SHARED_KEYWORD_CAP) * CANDIDATE_SHARED_KEYWORD_WEIGHT
        score += min(len(shared_entities), CANDIDATE_SHARED_ENTITY_CAP) * CANDIDATE_SHARED_ENTITY_WEIGHT
        if same_category:
            score += CANDIDATE_SAME_CATEGORY_BONUS
        if same_date_bucket:
            score += CANDIDATE_SAME_DATE_BUCKET_BONUS
        if title_similarity >= CANDIDATE_TITLE_SIMILARITY_THRESHOLD:
            score += title_similarity * CANDIDATE_TITLE_SIMILARITY_WEIGHT

        reasons: list[str] = []
        if shared_keywords:
            reasons.append(f"shared keywords: {', '.join(sorted(shared_keywords)[:4])}")
        if shared_entities:
            reasons.append(f"shared entities: {', '.join(sorted(shared_entities)[:3])}")
        if same_category:
            reasons.append("same category")
        if same_date_bucket:
            reasons.append("similar end date")
        if title_similarity >= CANDIDATE_TITLE_SIMILARITY_THRESHOLD:
            reasons.append(f"title similarity {title_similarity:.2f}")

        if not reasons and score > 0:
            reasons.append("heuristic overlap")

        return score, reasons

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in TOKEN_RE.findall(text)]

    def _normalize_text(self, text: str) -> str:
        return " ".join(self._tokenize(text))
