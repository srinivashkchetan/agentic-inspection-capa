// Mirror of the backend API contract (backend/app/schemas.py + models).

export interface ReportSummary {
  report_id: string;
  report_date: string | null;
  overall_result: "PASS" | "FAIL" | "PENDING";
  fail_code: string | null;
  failure_type: string;
  department: string | null;
  vendor: string | null;
  product: string | null;
  draftable: boolean;
}

export interface CorrectiveAction {
  step: number;
  description: string;
  citation: string;
  owner: string | null;
  due_date: string | null;
}

export type CapaStatus =
  | "draft"
  | "approved_hitl1"
  | "vendor_implementing"
  | "verifying"
  | "approved_hitl2"
  | "closed"
  | "rejected"
  | "escalated";

export interface CapaDraft {
  id: string;
  report_id: string;
  result_state: "PASS" | "FAIL" | "PENDING";
  failure_type: string;
  root_cause: string;
  containment: string;
  corrective_actions: CorrectiveAction[];
  verification_method: string;
  owner: string | null;
  due_date: string | null;
  status: CapaStatus;
  generated_by: string;
  citations: string[];
  guardrail_flags: string[];
  confidence: number;
  created_at: string;
  history: Array<Record<string, unknown>>;
}

// The full report is loosely typed — it carries many OCR fields (PRD §5.1).
export type InspectionReport = Record<string, unknown> & {
  report_id: string;
  overall_result: string;
  fail_code: string | null;
  fail_reason: string | null;
};
