import type { OpportunityDetail, OpportunityListItem, OpportunityType, RefreshResponse } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchOpportunities(opportunityType?: OpportunityType) {
  const params = new URLSearchParams({ sort: "score_desc" });
  if (opportunityType) {
    params.set("opportunity_type", opportunityType);
  }
  return request<OpportunityListItem[]>(`/opportunities?${params.toString()}`);
}

export function fetchOpportunity(id: string) {
  return request<OpportunityDetail>(`/opportunities/${id}`);
}

export function refreshPipeline() {
  return request<RefreshResponse>("/admin/refresh", { method: "POST" });
}

