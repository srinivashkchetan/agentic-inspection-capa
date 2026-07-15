import type { CapaDraft, InspectionReport, ReportSummary } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listReports: () => req<ReportSummary[]>("/reports"),
  getReport: (id: string) => req<InspectionReport>(`/reports/${id}`),
  draft: (id: string) => req<CapaDraft>(`/reports/${id}/draft`, { method: "POST" }),

  getCapa: (id: string) => req<CapaDraft>(`/capas/${id}`),
  approve: (id: string, note?: string) =>
    req<CapaDraft>(`/capas/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  reject: (id: string, note?: string) =>
    req<CapaDraft>(`/capas/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  submitEvidence: (id: string, note?: string) =>
    req<CapaDraft>(`/capas/${id}/submit-evidence`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  verify: (id: string, passed: boolean, note?: string) =>
    req<CapaDraft>(`/capas/${id}/verify`, {
      method: "POST",
      body: JSON.stringify({ passed, note }),
    }),
};
