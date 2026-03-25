from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

from app.models import Market
from app.schemas import RelationType


@dataclass(frozen=True)
class RelationAnalysisResult:
    relation_type: RelationType
    relation_strength: float
    confidence: float
    reasoning_summary: str
    detected_by: str


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
NUMBER_PATTERN = re.compile(
    r"\b(?P<op>at least|over|above|more than|under|below|less than)\s+(?P<value>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
BY_PATTERN = re.compile(
    r"\bby\s+(?P<value>(?:[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})|(?:[A-Za-z]{3,9}\s+\d{4})|(?:\d{4}-\d{2}-\d{2})|(?:end of \d{4})|(?:Q[1-4]\s+\d{4})|(?:\d{4}))",
    re.IGNORECASE,
)
WIN_PATTERN = re.compile(r"will\s+(?P<subject>.+?)\s+win\s+(?P<event>.+)", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


class RelationAnalyzer:
    def __init__(self, llm_service) -> None:
        self.llm_service = llm_service

    def analyze(self, market_a: Market, market_b: Market) -> RelationAnalysisResult:
        return self.analyze_pairs([(market_a, market_b)])[0]

    def analyze_pairs(self, market_pairs: Sequence[tuple[Market, Market]]) -> list[RelationAnalysisResult]:
        if not market_pairs:
            return []

        results: list[RelationAnalysisResult | None] = [None] * len(market_pairs)
        llm_inputs: list[tuple[Market, Market]] = []
        llm_indexes: list[int] = []
        pending_rule_results: dict[int, RelationAnalysisResult | None] = {}

        for index, (market_a, market_b) in enumerate(market_pairs):
            rule_result = self._rule_based(market_a, market_b)
            if rule_result and rule_result.confidence >= 0.9:
                results[index] = rule_result
                continue
            llm_inputs.append((market_a, market_b))
            llm_indexes.append(index)
            pending_rule_results[index] = rule_result

        llm_results = self.llm_service.analyze_relations(llm_inputs) if llm_inputs else []
        for offset, index in enumerate(llm_indexes):
            llm_result = llm_results[offset] if offset < len(llm_results) else None
            results[index] = self._resolve_result(pending_rule_results.get(index), llm_result)

        return [result if result is not None else self._fallback_result() for result in results]

    def _rule_based(self, market_a: Market, market_b: Market) -> RelationAnalysisResult | None:
        for detector in (
            self._detect_exclusive_winners,
            self._detect_deadline_subset,
            self._detect_threshold_subset,
            self._detect_near_duplicate_overlap,
        ):
            result = detector(market_a, market_b)
            if result is not None:
                return result
        return None

    def _detect_exclusive_winners(self, market_a: Market, market_b: Market) -> RelationAnalysisResult | None:
        match_a = WIN_PATTERN.search(market_a.title)
        match_b = WIN_PATTERN.search(market_b.title)
        if not match_a or not match_b:
            return None

        subject_a = self._normalize_text(match_a.group("subject"))
        subject_b = self._normalize_text(match_b.group("subject"))
        event_a = self._normalize_text(match_a.group("event"))
        event_b = self._normalize_text(match_b.group("event"))
        if subject_a == subject_b:
            return None

        similarity = SequenceMatcher(None, event_a, event_b).ratio()
        if similarity < 0.78:
            return None

        return RelationAnalysisResult(
            relation_type=RelationType.EXCLUSIVE,
            relation_strength=0.92,
            confidence=0.9,
            reasoning_summary="Both markets ask whether different subjects win what appears to be the same contest, so both cannot resolve true together.",
            detected_by="rule",
        )

    def _detect_deadline_subset(self, market_a: Market, market_b: Market) -> RelationAnalysisResult | None:
        parsed_a = self._extract_deadline(market_a.title)
        parsed_b = self._extract_deadline(market_b.title)
        if parsed_a is None or parsed_b is None:
            return None

        core_a, deadline_a = parsed_a
        core_b, deadline_b = parsed_b
        if SequenceMatcher(None, core_a, core_b).ratio() < 0.78 or deadline_a == deadline_b:
            return None

        if deadline_a < deadline_b:
            relation_type = RelationType.SUBSET
            summary = "Market A is the earlier-deadline version of the same event, so resolving true for A would also satisfy B."
        else:
            relation_type = RelationType.SUPERSET
            summary = "Market A is the later-deadline version of the same event, so market B is the narrower subset."

        return RelationAnalysisResult(
            relation_type=relation_type,
            relation_strength=0.88,
            confidence=0.84,
            reasoning_summary=summary,
            detected_by="rule",
        )

    def _detect_threshold_subset(self, market_a: Market, market_b: Market) -> RelationAnalysisResult | None:
        parsed_a = self._extract_threshold(market_a.title)
        parsed_b = self._extract_threshold(market_b.title)
        if parsed_a is None or parsed_b is None:
            return None

        core_a, op_a, value_a = parsed_a
        core_b, op_b, value_b = parsed_b
        if op_a != op_b or SequenceMatcher(None, core_a, core_b).ratio() < 0.8 or value_a == value_b:
            return None

        increasing_ops = {"at least", "over", "above", "more than"}
        if op_a in increasing_ops:
            relation_type = RelationType.SUBSET if value_a > value_b else RelationType.SUPERSET
        else:
            relation_type = RelationType.SUBSET if value_a < value_b else RelationType.SUPERSET

        return RelationAnalysisResult(
            relation_type=relation_type,
            relation_strength=0.86,
            confidence=0.82,
            reasoning_summary="The two markets differ mainly by a numeric threshold, making one a narrower version of the other.",
            detected_by="rule",
        )

    def _detect_near_duplicate_overlap(self, market_a: Market, market_b: Market) -> RelationAnalysisResult | None:
        similarity = SequenceMatcher(None, self._normalize_text(market_a.title), self._normalize_text(market_b.title)).ratio()
        if similarity < 0.88:
            return None

        return RelationAnalysisResult(
            relation_type=RelationType.OVERLAP,
            relation_strength=0.7,
            confidence=0.62,
            reasoning_summary="The titles are near-duplicates, but the rule set is not explicit enough to infer a harder logical relation.",
            detected_by="rule",
        )

    def _merge_results(
        self,
        rule_result: RelationAnalysisResult,
        llm_result: RelationAnalysisResult,
    ) -> RelationAnalysisResult:
        if rule_result.relation_type == llm_result.relation_type:
            return RelationAnalysisResult(
                relation_type=llm_result.relation_type,
                relation_strength=round((rule_result.relation_strength + llm_result.relation_strength) / 2, 3),
                confidence=round((rule_result.confidence + llm_result.confidence) / 2, 3),
                reasoning_summary=f"{rule_result.reasoning_summary} {llm_result.reasoning_summary}".strip(),
                detected_by="hybrid",
            )

        if abs(rule_result.confidence - llm_result.confidence) <= 0.1:
            return RelationAnalysisResult(
                relation_type=RelationType.AMBIGUOUS,
                relation_strength=min(rule_result.relation_strength, llm_result.relation_strength),
                confidence=max(rule_result.confidence, llm_result.confidence) - 0.1,
                reasoning_summary=(
                    f"Rule-based analysis suggested {rule_result.relation_type.value}; "
                    f"LLM suggested {llm_result.relation_type.value}. The conflict is too close to treat as reliable."
                ),
                detected_by="hybrid",
            )

        winner = rule_result if rule_result.confidence > llm_result.confidence else llm_result
        return RelationAnalysisResult(
            relation_type=winner.relation_type,
            relation_strength=winner.relation_strength,
            confidence=winner.confidence,
            reasoning_summary=winner.reasoning_summary,
            detected_by="hybrid",
        )

    def _resolve_result(
        self,
        rule_result: RelationAnalysisResult | None,
        llm_result: RelationAnalysisResult | None,
    ) -> RelationAnalysisResult:
        if rule_result and llm_result:
            return self._merge_results(rule_result, llm_result)
        if llm_result:
            return llm_result
        if rule_result:
            return rule_result
        return self._fallback_result()

    def _fallback_result(self) -> RelationAnalysisResult:
        return RelationAnalysisResult(
            relation_type=RelationType.AMBIGUOUS,
            relation_strength=0.1,
            confidence=0.15,
            reasoning_summary="No rule-based relation was strong enough and no LLM verdict was available.",
            detected_by="rule",
        )

    def _extract_deadline(self, text: str) -> tuple[str, datetime] | None:
        match = BY_PATTERN.search(text)
        if not match:
            return None

        deadline = self._parse_deadline_value(match.group("value"))
        if deadline is None:
            return None

        core = self._normalize_text(BY_PATTERN.sub("", text))
        return core, deadline

    def _extract_threshold(self, text: str) -> tuple[str, str, float] | None:
        match = NUMBER_PATTERN.search(text)
        if not match:
            return None

        op = match.group("op").lower()
        try:
            value = float(match.group("value"))
        except ValueError:
            return None
        core = self._normalize_text(NUMBER_PATTERN.sub("", text))
        return core, op, value

    def _parse_deadline_value(self, text: str) -> datetime | None:
        clean = text.strip().replace(",", "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean):
            return datetime.fromisoformat(clean)
        if re.fullmatch(r"\d{4}", clean):
            return datetime(int(clean), 12, 31)

        quarter_match = re.fullmatch(r"Q([1-4])\s+(\d{4})", clean, flags=re.IGNORECASE)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            year = int(quarter_match.group(2))
            month = quarter * 3
            return datetime(year, month, 28)

        end_match = re.fullmatch(r"end of (\d{4})", clean, flags=re.IGNORECASE)
        if end_match:
            return datetime(int(end_match.group(1)), 12, 31)

        parts = clean.split()
        if len(parts) == 2 and parts[0].lower() in MONTHS and parts[1].isdigit():
            return datetime(int(parts[1]), MONTHS[parts[0].lower()], 28)
        if len(parts) == 3 and parts[0].lower() in MONTHS and parts[1].isdigit() and parts[2].isdigit():
            return datetime(int(parts[2]), MONTHS[parts[0].lower()], int(parts[1]))
        return None

    def _normalize_text(self, text: str) -> str:
        return " ".join(token.lower() for token in TOKEN_RE.findall(text))
