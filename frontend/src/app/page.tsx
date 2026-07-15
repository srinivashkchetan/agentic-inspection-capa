"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ReportSummary } from "@/lib/types";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listReports()
      .then(setReports)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading reports…</p>;
  if (error)
    return (
      <p className="err">
        {error} — is the API running at{" "}
        <code>{process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}</code>?
      </p>
    );

  return (
    <>
      <p className="muted">
        {reports.length} inspection reports. FAIL / PENDING reports can be drafted into a CAPA.
      </p>
      <table>
        <thead>
          <tr>
            <th>Report</th>
            <th>Date</th>
            <th>Result</th>
            <th>Code</th>
            <th>Failure type</th>
            <th>Department</th>
            <th>Vendor</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.report_id}>
              <td>
                <Link href={`/reports/${r.report_id}`}>{r.report_id}</Link>
              </td>
              <td className="muted">{r.report_date ?? "—"}</td>
              <td>
                <span className={`badge ${r.overall_result}`}>{r.overall_result}</span>
              </td>
              <td className="muted">{r.fail_code ?? "—"}</td>
              <td>{r.failure_type}</td>
              <td className="muted">{r.department ?? "—"}</td>
              <td className="muted">{r.vendor ?? "—"}</td>
              <td>{r.draftable ? <Link href={`/reports/${r.report_id}`}>review →</Link> : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
