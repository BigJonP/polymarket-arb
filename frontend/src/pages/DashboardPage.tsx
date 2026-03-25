import { useEffect, useState } from "react";

import { fetchOpportunities, refreshPipeline } from "../api/client";
import { OpportunityCard } from "../components/OpportunityCard";
import { OpportunityTable } from "../components/OpportunityTable";
import type { OpportunityListItem, OpportunityType, RefreshResponse } from "../types/api";

const FILTERS: Array<{ label: string; value?: OpportunityType }> = [
  { label: "All" },
  { label: "Hard arb", value: "hard_arb" },
  { label: "Structural mispricing", value: "structural_mispricing" },
  { label: "Soft dislocation", value: "soft_dislocation" },
];

export function DashboardPage() {
  const [items, setItems] = useState<OpportunityListItem[]>([]);
  const [selectedType, setSelectedType] = useState<OpportunityType | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshResult, setRefreshResult] = useState<RefreshResponse | null>(null);

  useEffect(() => {
    void loadOpportunities(selectedType);
  }, [selectedType]);

  async function loadOpportunities(type?: OpportunityType) {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchOpportunities(type);
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load opportunities.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    try {
      setRefreshing(true);
      setError(null);
      const result = await refreshPipeline();
      setRefreshResult(result);
      await loadOpportunities(selectedType);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed.");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-black/10 bg-white/85 p-6 shadow-card backdrop-blur">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.3em] text-slate">Opportunity feed</div>
            <h1 className="max-w-3xl text-3xl font-semibold leading-tight">
              Cross-market inconsistencies, relative-value setups, and only the rare cases that look like hard arb.
            </h1>
            <p className="max-w-3xl text-sm text-slate">
              The scanner combines heuristic pairing, conservative relation analysis, and price checks across active Polymarket markets.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={refreshing}
              className="rounded-full bg-ink px-5 py-3 text-sm font-medium text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
            >
              {refreshing ? "Refreshing..." : "Run refresh"}
            </button>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {FILTERS.map((filter) => {
            const isSelected = filter.value === selectedType || (!filter.value && !selectedType);
            return (
              <button
                key={filter.label}
                type="button"
                onClick={() => setSelectedType(filter.value)}
                className={`rounded-full border px-4 py-2 text-sm transition ${
                  isSelected ? "border-ink bg-ink text-white" : "border-black/10 bg-white text-slate hover:border-black/20"
                }`}
              >
                {filter.label}
              </button>
            );
          })}
        </div>

        {refreshResult ? (
          <div className="mt-5 rounded-2xl border border-accent/20 bg-accent/5 px-4 py-3 text-sm text-slate">
            Refresh complete: fetched {refreshResult.markets_fetched} markets, analyzed {refreshResult.candidate_pairs} candidate pairs, and stored{" "}
            {refreshResult.opportunities_upserted} active opportunities.
          </div>
        ) : null}

        {error ? (
          <div className="mt-5 rounded-2xl border border-warning/20 bg-warning/5 px-4 py-3 text-sm text-warning">{error}</div>
        ) : null}
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-[24px] border border-black/10 bg-white p-5 shadow-card">
          <div className="text-xs uppercase tracking-[0.22em] text-slate">Visible setups</div>
          <div className="mt-3 text-4xl font-semibold">{items.length}</div>
        </div>
        <div className="rounded-[24px] border border-black/10 bg-white p-5 shadow-card">
          <div className="text-xs uppercase tracking-[0.22em] text-slate">Avg score</div>
          <div className="mt-3 text-4xl font-semibold">
            {items.length ? (items.reduce((sum, item) => sum + item.opportunity.score, 0) / items.length).toFixed(0) : "0"}
          </div>
        </div>
        <div className="rounded-[24px] border border-black/10 bg-white p-5 shadow-card">
          <div className="text-xs uppercase tracking-[0.22em] text-slate">Top relation</div>
          <div className="mt-3 text-2xl font-semibold capitalize">
            {items[0]?.relation.relation_type.replace(/_/g, " ") ?? "none"}
          </div>
        </div>
      </section>

      <section>
        {loading ? (
          <div className="rounded-[28px] border border-black/10 bg-white p-8 text-center text-slate shadow-card">Loading opportunities...</div>
        ) : items.length === 0 ? (
          <div className="rounded-[28px] border border-black/10 bg-white p-8 text-center text-slate shadow-card">
            No active opportunities match the current filter.
          </div>
        ) : (
          <>
            <div className="space-y-4 lg:hidden">
              {items.map((item) => (
                <OpportunityCard key={item.opportunity.id} item={item} />
              ))}
            </div>
            <div className="hidden lg:block">
              <OpportunityTable items={items} />
            </div>
          </>
        )}
      </section>
    </div>
  );
}
