from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import get_settings


@dataclass
class NormalizedMarket:
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
    raw_payload: dict[str, Any]
    fetched_at: datetime


class PolymarketClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_active_markets(self) -> list[NormalizedMarket]:
        markets: list[NormalizedMarket] = []
        offset = 0

        with httpx.Client(base_url=self.settings.polymarket_api_base_url, timeout=self.settings.request_timeout_seconds) as client:
            for _ in range(self.settings.polymarket_max_pages):
                response = client.get(
                    "/markets",
                    params={
                        "closed": "false",
                        "limit": self.settings.polymarket_page_size,
                        "offset": offset,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                rows = self._unwrap_rows(payload)
                if not rows:
                    break

                fetched_at = datetime.now(UTC)
                for row in rows:
                    normalized = self._normalize_market(row, fetched_at)
                    if normalized is not None:
                        markets.append(normalized)

                if len(rows) < self.settings.polymarket_page_size:
                    break
                offset += self.settings.polymarket_page_size

        return markets

    def _unwrap_rows(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            items = payload.get("data") or payload.get("markets") or payload.get("items") or []
            if isinstance(items, list):
                return [row for row in items if isinstance(row, dict)]
        return []

    def _normalize_market(self, row: dict[str, Any], fetched_at: datetime) -> NormalizedMarket | None:
        external_id = self._pick_external_id(row)
        title = self._pick_title(row)
        if not external_id or not title:
            return None

        return NormalizedMarket(
            external_id=external_id,
            title=title,
            description=self._pick_text(row, "description", "subtitle"),
            rules=self._pick_text(row, "rules", "resolutionCriteria", "resolution_criteria", "resolutionSource"),
            category=self._pick_text(row, "category", "subcategory"),
            end_date=self._parse_datetime(
                row.get("endDate") or row.get("endDateIso") or row.get("end_date") or row.get("closedTime")
            ),
            active=bool(row.get("active", True)) and not bool(row.get("closed", False)) and not bool(row.get("archived", False)),
            outcomes_json=self._coerce_jsonish(row.get("outcomes") or row.get("tokens") or row.get("outcomeNames")),
            prices_json=self._coerce_jsonish(row.get("outcomePrices") or row.get("prices") or row.get("tokenPrices")),
            volume=self._coerce_float(row.get("volume") or row.get("volumeNum")),
            liquidity=self._coerce_float(row.get("liquidity") or row.get("liquidityNum")),
            raw_payload=row,
            fetched_at=fetched_at,
        )

    def _pick_external_id(self, row: dict[str, Any]) -> str | None:
        for key in ("id", "conditionId", "condition_id", "slug"):
            value = row.get(key)
            if value is not None:
                return str(value)
        return None

    def _pick_title(self, row: dict[str, Any]) -> str | None:
        return self._pick_text(row, "question", "title", "marketTitle", "slug")

    def _pick_text(self, row: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _coerce_jsonish(self, value: Any) -> list | dict | None:
        if value is None:
            return None
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                loaded = json.loads(value)
                if isinstance(loaded, (list, dict)):
                    return loaded
            except json.JSONDecodeError:
                pass
        return {"value": value}

    def _coerce_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
