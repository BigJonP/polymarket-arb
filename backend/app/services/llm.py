from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Sequence

import httpx

from app.config import get_settings
from app.models import Market
from app.schemas import RelationType

from app.services.relation_analysis import RelationAnalysisResult


class BaseLLMService(ABC):
    def analyze_relation(self, market_a: Market, market_b: Market) -> RelationAnalysisResult | None:
        results = self.analyze_relations([(market_a, market_b)])
        return results[0] if results else None

    @abstractmethod
    def analyze_relations(self, market_pairs: Sequence[tuple[Market, Market]]) -> list[RelationAnalysisResult | None]:
        raise NotImplementedError


class NullLLMService(BaseLLMService):
    def analyze_relations(self, market_pairs: Sequence[tuple[Market, Market]]) -> list[RelationAnalysisResult | None]:
        return [None] * len(market_pairs)


class OpenAILLMService(BaseLLMService):
    def __init__(self) -> None:
        self.settings = get_settings()

    def analyze_relations(self, market_pairs: Sequence[tuple[Market, Market]]) -> list[RelationAnalysisResult | None]:
        if not market_pairs:
            return []

        results: list[RelationAnalysisResult | None] = []
        batch_size = max(1, self.settings.openai_batch_size)
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}

        with httpx.Client(base_url=self.settings.openai_base_url, timeout=self.settings.request_timeout_seconds) as client:
            for batch_start in range(0, len(market_pairs), batch_size):
                batch = market_pairs[batch_start : batch_start + batch_size]
                response = client.post("/chat/completions", json=self._build_batch_payload(batch), headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                results.extend(self._parse_batch_response(content, expected_size=len(batch)))

        return results

    def _clamp(self, value: object, default: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, numeric))

    def _build_batch_payload(self, market_pairs: Sequence[tuple[Market, Market]]) -> dict:
        return {
            "model": self.settings.openai_model,
            "temperature": 0.1,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "market_relation_batch",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "results": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "pair_index": {"type": "integer"},
                                        "relation_type": {
                                            "type": "string",
                                            "enum": [relation_type.value for relation_type in RelationType],
                                        },
                                        "relation_strength": {"type": "number"},
                                        "confidence": {"type": "number"},
                                        "reasoning_summary": {"type": "string"},
                                    },
                                    "required": [
                                        "pair_index",
                                        "relation_type",
                                        "relation_strength",
                                        "confidence",
                                        "reasoning_summary",
                                    ],
                                },
                            }
                        },
                        "required": ["results"],
                    },
                },
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You compare prediction market pairs in batches. "
                        "Be conservative, avoid false arbitrage claims, and only identify clear logical "
                        "or probabilistic relations. "
                        "Use exclusive, implies, implied_by, subset, superset, negative_correlation, "
                        "or positive_correlation only when the markets clearly share the same underlying "
                        "subject, event, threshold, deadline, or named entity. "
                        "If they do not share a clear anchor, prefer unrelated or ambiguous. "
                        "Return a single JSON object with a top-level 'results' array. "
                        "Each array item must include pair_index, relation_type, relation_strength, confidence, reasoning_summary. "
                        "relation_type is relative to market A versus market B and must be one of: "
                        "exclusive, implies, implied_by, subset, superset, negative_correlation, "
                        "positive_correlation, overlap, unrelated, ambiguous. "
                        "Do not return markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "pairs": [
                                {
                                    "pair_index": pair_index,
                                    "market_a": {
                                        "title": market_a.title,
                                        "description": market_a.description,
                                        "rules": market_a.rules,
                                        "category": market_a.category,
                                    },
                                    "market_b": {
                                        "title": market_b.title,
                                        "description": market_b.description,
                                        "rules": market_b.rules,
                                        "category": market_b.category,
                                    },
                                }
                                for pair_index, (market_a, market_b) in enumerate(market_pairs)
                            ]
                        }
                    ),
                },
            ],
        }

    def _parse_batch_response(self, content: object, expected_size: int) -> list[RelationAnalysisResult | None]:
        results: list[RelationAnalysisResult | None] = [None] * expected_size
        if not content or not isinstance(content, str):
            return results

        try:
            payload = json.loads(content)
            rows = payload.get("results", [])
            if not isinstance(rows, list):
                return results
            for row in rows:
                if not isinstance(row, dict):
                    continue
                pair_index = row.get("pair_index")
                if not isinstance(pair_index, int) or pair_index < 0 or pair_index >= expected_size:
                    continue
                results[pair_index] = RelationAnalysisResult(
                    relation_type=RelationType(row["relation_type"]),
                    relation_strength=self._clamp(row.get("relation_strength"), default=0.0),
                    confidence=self._clamp(row.get("confidence"), default=0.0),
                    reasoning_summary=str(row.get("reasoning_summary", "")).strip() or "LLM did not provide reasoning.",
                    detected_by="llm",
                )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return results

        return results


def build_llm_service() -> BaseLLMService:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAILLMService()
    return NullLLMService()
