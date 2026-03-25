import { Link } from "react-router-dom";

import type { OpportunityListItem } from "../types/api";

function formatPct(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return "n/a";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function getProbability(prices: unknown, outcomes: unknown) {
  if (prices && typeof prices === "object" && !Array.isArray(prices)) {
    const entries = Object.entries(prices as Record<string, unknown>);
    const yesEntry = entries.find(([key]) => key.toLowerCase() === "yes");
    if (yesEntry) {
      return normalizeProbability(yesEntry[1]);
    }
    return normalizeProbability(entries[0]?.[1]);
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

export function OpportunityTable({ items }: { items: OpportunityListItem[] }) {
  return (
    <div className="overflow-hidden rounded-[28px] border border-black/10 bg-white shadow-card">
      <div className="hidden overflow-x-auto lg:block">
        <table className="min-w-full divide-y divide-black/5 text-sm">
          <thead className="bg-ink text-left text-xs uppercase tracking-[0.18em] text-white/75">
            <tr>
              <th className="px-5 py-4 font-medium">Opportunity</th>
              <th className="px-5 py-4 font-medium">Relation</th>
              <th className="px-5 py-4 font-medium">Markets</th>
              <th className="px-5 py-4 font-medium">Prices</th>
              <th className="px-5 py-4 font-medium">Summary</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-black/5">
            {items.map((item) => {
              const priceA = getProbability(item.market_a.prices_json, item.market_a.outcomes_json);
              const priceB = getProbability(item.market_b.prices_json, item.market_b.outcomes_json);
              return (
                <tr key={item.opportunity.id} className="align-top transition hover:bg-black/[0.025]">
                  <td className="px-5 py-4">
                    <Link to={`/opportunities/${item.opportunity.id}`} className="space-y-2">
                      <div className="flex items-center gap-3">
                        <div className="text-3xl font-semibold leading-none">{item.opportunity.score.toFixed(0)}</div>
                        <span className={`rounded-full px-3 py-1 text-xs font-medium ${badgeColor(item.opportunity.opportunity_type)}`}>
                          {item.opportunity.opportunity_type.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="font-medium text-ink">{item.opportunity.headline}</div>
                    </Link>
                  </td>
                  <td className="px-5 py-4">
                    <div className="font-medium capitalize">{item.relation.relation_type.replace(/_/g, " ")}</div>
                    <div className="mt-1 text-slate">
                      confidence {(item.relation.confidence * 100).toFixed(0)}% · {item.relation.detected_by}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-slate">
                    <div>{item.market_a.title}</div>
                    <div className="mt-2">{item.market_b.title}</div>
                  </td>
                  <td className="px-5 py-4 font-mono text-xs text-slate">
                    <div>A {formatPct(priceA)}</div>
                    <div className="mt-2">B {formatPct(priceB)}</div>
                  </td>
                  <td className="px-5 py-4 text-slate">{item.opportunity.summary}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
