"""Contract tests for the JSON API the Next.js console depends on."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_reports() -> None:
    r = client.get("/reports")
    assert r.status_code == 200
    rows = r.json()
    assert rows and "failure_type" in rows[0] and "draftable" in rows[0]


def test_draft_then_hitl_flow() -> None:
    reports = client.get("/reports").json()
    # Workmanship FAILs draft a real CAPA (compliance-only ones escalate).
    fail = next(
        x
        for x in reports
        if x["overall_result"] == "FAIL" and x["failure_type"] == "workmanship"
    )

    draft = client.post(f"/reports/{fail['report_id']}/draft")
    assert draft.status_code == 201
    capa = draft.json()
    capa_id = capa["id"]
    assert capa["corrective_actions"]
    assert capa["status"] == "draft"

    approved = client.post(f"/capas/{capa_id}/approve", json={"note": "looks good"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "vendor_implementing"

    client.post(f"/capas/{capa_id}/submit-evidence")
    verified = client.post(f"/capas/{capa_id}/verify", json={"passed": True})
    assert verified.json()["status"] == "closed"


def test_pass_report_draft_conflicts() -> None:
    reports = client.get("/reports").json()
    ok = next(x for x in reports if x["overall_result"] == "PASS")
    r = client.post(f"/reports/{ok['report_id']}/draft")
    assert r.status_code == 409
