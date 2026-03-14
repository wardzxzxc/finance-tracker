export type GroupBy = "category" | "payment_method";

export interface SummaryGroup {
  id: string;
  name: string;
  color: string;
  amount: number;
  percentage: number;
}

export interface SummaryResponse {
  month: number;
  year: number;
  group_by: GroupBy;
  total: number;
  groups: SummaryGroup[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function getExpenseSummary(
  month: number,
  year: number,
  groupBy: GroupBy
): Promise<SummaryResponse> {
  const params = new URLSearchParams({
    month: String(month),
    year: String(year),
    group_by: groupBy,
  });
  const resp = await fetch(`${API_BASE}/transactions/summary?${params}`, {
    headers: {
      "X-API-Key": import.meta.env.VITE_API_KEY ?? "",
    },
  });
  if (!resp.ok) {
    throw new Error(`Failed to fetch summary: ${resp.status}`);
  }
  return resp.json() as Promise<SummaryResponse>;
}
