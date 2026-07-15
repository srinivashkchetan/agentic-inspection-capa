"""API response/request shapes that aren't domain models."""

from __future__ import annotations

from pydantic import BaseModel

from app.models import InspectionReport
from app.pipeline import classify


class ReportSummary(BaseModel):
    """Lightweight row for the report list in the review console."""

    report_id: str
    report_date: str | None
    overall_result: str
    fail_code: str | None
    failure_type: str
    department: str | None
    vendor: str | None
    product: str | None
    draftable: bool

    @classmethod
    def from_report(cls, r: InspectionReport) -> "ReportSummary":
        g = r.general
        product = r.products[0].description if r.products else None
        return cls(
            report_id=r.report_id,
            report_date=r.report_date,
            overall_result=r.overall_result,
            fail_code=r.fail_code,
            failure_type=classify.classify_failure_type(r).value,
            department=g.department_name if g else None,
            vendor=g.vendor_supplier_name if g else None,
            product=product,
            draftable=classify.should_draft(r),
        )


class VerifyRequest(BaseModel):
    passed: bool
    note: str | None = None


class ActorNote(BaseModel):
    note: str | None = None
