import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchOpportunity } from "../api/client";
import type { Market, OpportunityDetail } from "../types/api";

function normalizeProbability(value: unknown) {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return null;
  }
  return numeric > 1 ? numeric / 100 : numeric;
}

function extractProbability(market: Market) {
  if (market.prices_json && typeof market.prices_json === "object" && !Array.isArray(market.prices_json)) {
    const entries = Object.entries(market.prices_json as Record<string, unknown>);
    const yesEntry = entries.find(([key]) => key.toLowerCase() === "yes");
    return normalizeProbability(yesEntry?.[1] ?? entries[0]?.[1]);
  }
  if (Array.isArray(market.prices_json)) {
    if (Array.isArray(market.outcomes_json)) {
      const yesIndex = market.outcomes_json.findIndex((outcome) => String(outcome).toLowerCase() === "yes");
      if (yesIndex >= 0) {
        return normalizeProbability(market.prices_json[yesIndex]);
      }
    }
    return normalizeProbability(market.prices_json[0]);
  }
  return null;
}

function renderProbability(market: Market) {
  const probability = extractProbability(market);
  return probability === null ? "n/a" : `${(probability * 100).toFixed(1)}%`;
}

function MarketPanel({ market, label }: { market: Market; label: string }) {
  return (
    <div className="rounded-[28px] border border-black/10 bg-white p-6 shadow-card">
      <div className="text-xs uppercase tracking-[0.22em] text-slate">{label}</div>
      <h2 className="mt-3 text-xl font-semibold leading-snug">{market.title}</h2>
      <div className="mt-4 grid gap-3 text-sm text-slate sm:grid-cols-2">
        <div>
          <div className="text-xs uppercase tracking-[0.18em]">Category</div>
          <div className="mt-1 text-ink">{market.category ?? "n/a"}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.18em]">Primary price</div>
          <div className="mt-1 font-mono text-ink">{renderProbability(market)}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.18em]">Volume</div>
          <div className="mt-1 text-ink">{market.volume?.toFixed(2) ?? "n/a"}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.18em]">Liquidity</div>
          <div className="mt-1 text-ink">{market.liquidity?.toFixed(2) ?? "n/a"}</div>
        </div>
      </div>

      <div className="mt-5 space-y-4 text-sm text-slate">
        <div>
          <div className="text-xs uppercase tracking-[0.18em]">Description</div>
          <div className="mt-1">{market.description ?? "n/a"}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.18em]">Rules / resolution</div>
          <div className="mt-1">{market.rules ?? "n/a"}</div>
        </div>
      </div>

      <div className="mt-5">
        <div className="text-xs uppercase tracking-[0.18em] text-slate">Raw market payload</div>
        <pre className="mt-2 max-h-[320px] overflow-auto rounded-2xl bg-ink p-4 font-mono text-xs text-white/85">
          {JSON.stringify(market.raw_payload, null, 2)}
        </pre>
      </div>
    </div>
  );
}

export function OpportunityDetailPage() {
  const { id } = useParams();
  const [detail, setDetail] = useState<OpportunityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setError("Missing opportunity id.");
      setLoading(false);
      return;
    }

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchOpportunity(id);
        setDetail(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load opportunity.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id]);

  if (loading) {
    return <div className="rounded-[28px] border border-black/10 bg-white p-8 text-center text-slate shadow-card">Loading detail view...</div>;
  }

  if (error || !detail) {
    return (
      <div className="space-y-4">
        <Link to="/" className="text-sm text-slate underline">
          Back to dashboard
        </Link>
        <div className="rounded-[28px] border border-warning/20 bg-white p-8 text-warning shadow-card">
          {error ?? "Opportunity not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/" className="text-sm text-slate underline">
          Back to dashboard
        </Link>
      </div>

      <section className="rounded-[32px] border border-black/10 bg-white p-6 shadow-card">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4">
            <div className="text-xs uppercase tracking-[0.3em] text-slate">{detail.opportunity.opportunity_type.replace(/_/g, " ")}</div>
            <h1 className="max-w-4xl text-3xl font-semibold leading-tight">{detail.opportunity.headline}</h1>
            <p className="max-w-4xl text-sm text-slate">{detail.opportunity.summary}</p>
          </div>

          <div className="rounded-[28px] bg-ink px-6 py-5 text-white">
            <div className="text-xs uppercase tracking-[0.22em] text-white/60">Score</div>
            <div className="mt-2 text-5xl font-semibold">{detail.opportunity.score.toFixed(0)}</div>
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <div className="rounded-[24px] bg-fog p-5">
            <div className="text-xs uppercase tracking-[0.2em] text-slate">Trade idea</div>
            <div className="mt-2 text-sm text-ink">{detail.opportunity.trade_idea}</div>
          </div>
          <div className="rounded-[24px] bg-fog p-5">
            <div className="text-xs uppercase tracking-[0.2em] text-slate">Risk notes</div>
            <div className="mt-2 text-sm text-ink">{detail.opportunity.risk_notes}</div>
          </div>
          <div className="rounded-[24px] bg-fog p-5">
            <div className="text-xs uppercase tracking-[0.2em] text-slate">Relation</div>
            <div className="mt-2 text-sm text-ink capitalize">{detail.relation.relation_type.replace(/_/g, " ")}</div>
            <div className="mt-1 text-sm text-slate">
              confidence {(detail.relation.confidence * 100).toFixed(0)}% · strength {(detail.relation.relation_strength * 100).toFixed(0)}% ·{" "}
              {detail.relation.detected_by}
            </div>
            <div className="mt-3 text-sm text-ink">{detail.relation.reasoning_summary}</div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <MarketPanel market={detail.market_a} label="Market A" />
        <MarketPanel market={detail.market_b} label="Market B" />
      </section>
    </div>
  );
}
