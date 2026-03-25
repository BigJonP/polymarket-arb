export type RelationType =
  | "exclusive"
  | "implies"
  | "implied_by"
  | "subset"
  | "superset"
  | "negative_correlation"
  | "positive_correlation"
  | "overlap"
  | "unrelated"
  | "ambiguous";

export type OpportunityType = "hard_arb" | "structural_mispricing" | "soft_dislocation";

export interface Market {
  id: number;
  external_id: string;
  title: string;
  description: string | null;
  rules: string | null;
  category: string | null;
  end_date: string | null;
  active: boolean;
  outcomes_json: unknown;
  prices_json: unknown;
  volume: number | null;
  liquidity: number | null;
  raw_payload: Record<string, unknown>;
  fetched_at: string;
}

export interface Relation {
  id: number;
  market_a_id: number;
  market_b_id: number;
  relation_type: RelationType;
  relation_strength: number;
  confidence: number;
  reasoning_summary: string;
  detected_by: string;
}

export interface Opportunity {
  id: number;
  relation_id: number;
  opportunity_type: OpportunityType;
  score: number;
  headline: string;
  summary: string;
  trade_idea: string;
  risk_notes: string;
  active: boolean;
}

export interface OpportunityListItem {
  opportunity: Opportunity;
  relation: Relation;
  market_a: Market;
  market_b: Market;
}

export interface OpportunityDetail {
  opportunity: Opportunity;
  relation: Relation;
  market_a: Market;
  market_b: Market;
}

export interface RefreshResponse {
  markets_fetched: number;
  active_markets: number;
  candidate_pairs: number;
  relations_upserted: number;
  opportunities_upserted: number;
}

