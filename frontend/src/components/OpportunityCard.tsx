import { Link } from "react-router-dom";

import type { OpportunityListItem } from "../types/api";

function formatPct(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return "n/a";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function extractProbability(prices: unknown, outcomes: unknown) {
  if (prices && typeof prices === "object" && !Array.isArray(prices)) {
    const entries = Object.entries(prices as Record<string, unknown>);
    const yesEntry = entries.find(([key]) => key.toLowerCase() === "yes");
    return normalizeProbability(yesEntry?.[1] ?? entries[0]?.[1]);
  }
  if (Array.isArray(prices)) {
    if (Array.isArray(outcomes)) {
      const yesIndex = outcomes.findIndex((outcome) => String(outcome).toLowerCase() === "yes");
      if (yesIndex >= 0) {
        return normalizeProbability(prices[yesIndex]);
      }
    }
    return normalizeProbability(prices[0]);
  }
  return null;
}

function normalizeProbability(value: unknown) {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return null;
  }
  return numeric > 1 ? numeric / 100 : numeric;
}

function badgeColor(type: OpportunityListItem["opportunity"]["opportunity_type"]) {
  if (type === "hard_arb") {
    return "bg-ink text-white";
  }
  if (type === "structural_mispricing") {
    return "bg-warning/10 text-warning";
  }
  return "bg-accent/10 text-accent";
}

export function OpportunityCard({ item }: { item: OpportunityListItem }) {
  const priceA = extractProbability(item.market_a.prices_json, item.market_a.outcomes_json);
  const priceB = extractProbability(item.market_b.prices_json, item.market_b.outcomes_json);

  return (
    <Link
      to={`/opportunities/${item.opportunity.id}`}
      className="block rounded-[24px] border border-black/10 bg-white p-5 shadow-card transition hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-3xl font-semibold">{item.opportunity.score.toFixed(0)}</div>
          <div className="mt-2 text-lg font-medium">{item.opportunity.headline}</div>
        </div>
        <div className={`rounded-full px-3 py-1 text-xs font-medium ${badgeColor(item.opportunity.opportunity_type)}`}>
          {item.opportunity.opportunity_type.replace(/_/g, " ")}
        </div>
      </div>

      <div className="mt-4 text-sm text-slate">{item.opportunity.summary}</div>

      <div className="mt-4 rounded-2xl bg-fog/80 p-4 text-sm text-slate">
        <div className="font-medium text-ink capitalize">{item.relation.relation_type.replace(/_/g, " ")}</div>
        <div className="mt-2">{item.market_a.title}</div>
        <div className="mt-1">{item.market_b.title}</div>
        <div className="mt-3 font-mono text-xs">
          A {formatPct(priceA)} · B {formatPct(priceB)}
        </div>
      </div>
    </Link>
  );
}
