"""Typed model of a third-party Final Random Inspection (FRI) report.

Mirrors the grounded input data model in PRD §5.1 and the seed dataset
`inspection_reports_all.json`. Fields are permissive (Optional + extra allowed)
because real reports are OCR-transcribed and some multi-value fields are
captured representatively (see the dataset "Data note").
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    # Tolerate additional / evolving fields from OCR without dropping them.
    model_config = ConfigDict(extra="allow")


class Aql(_Base):
    critical: str | float | None = None
    major: float | str | None = None
    minor: float | str | None = None


class Defect(_Base):
    defect_code: str | None = None
    defect_description: str | None = None
    critical: int = 0
    major: int = 0
    minor: int = 0


class CheckSection(_Base):
    """Sections E–H: visual/workmanship, packing, functional, on-site (PRD §5.1)."""

    inspection_standard: str | None = None
    inspection_level: str | None = None
    sampling_plan: str | None = None
    sample_size: int | str | None = None
    aql: Aql | None = None
    accept_reject: dict[str, int] | None = None
    defects: list[Defect] = Field(default_factory=list)
    total_found: dict[str, int] | None = None
    result: str | None = None


class Product(_Base):
    po_number: str | None = None
    item_number: str | None = None
    style_number: str | None = None
    description: str | None = None
    wm_private_brand: str | None = None
    wm_private_brand_name: str | None = None


class General(_Base):
    vendor_supplier_name: str | None = None
    vendor_supplier_id: str | None = None
    factory_name: str | None = None
    factory_id: str | None = None
    credit_office_code: str | None = None
    retail_market: str | None = None
    department_cat_no: str | None = None
    department_name: str | None = None
    product_category: str | None = None
    country_of_origin: str | None = None
    ifi_version: str | None = None
    approved_sample: str | None = None
    reference_sample: str | None = None
    protocol_no: str | None = None
    inspection_date: str | None = None


class Quantity(_Base):
    order_quantity_units: int | None = None
    shipment_quantity_units: int | None = None
    presented_units: int | None = None
    units_packed_pct: float | None = None


class OnsiteTest(_Base):
    check_point: str | None = None
    sample_size: str | None = None
    findings: str | None = None
    result: str | None = None


class InspectionReport(_Base):
    source: str | None = None  # "actual" | "synthetic"
    source_file: str | None = None
    report_id: str
    third_party_name: str | None = None
    third_party_inspection_no: str | None = None
    report_date: str | None = None
    overall_result: str  # PASS | FAIL | PENDING
    fail_code: str | None = None  # F-series (e.g. F8) or P-series (e.g. P2)
    fail_reason: str | None = None
    service_performed: str | None = None
    inspection_type_flag: str | None = None

    general: General | None = None
    products: list[Product] = Field(default_factory=list)
    quantity: Quantity | None = None
    result_summary: dict[str, str] = Field(default_factory=dict)

    visual_check: CheckSection | None = None
    packing_check: CheckSection | None = None
    functional_measurement: CheckSection | None = None
    onsite_tests: list[OnsiteTest] = Field(default_factory=list)

    attachments: dict[str, object] | None = None
    inspection: dict[str, object] | None = None
    remarks: list[str] = Field(default_factory=list)
