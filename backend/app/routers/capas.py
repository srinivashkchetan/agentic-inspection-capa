"""CAPA endpoints: the two human-in-the-loop gates (PRD §5 closed loop).

HITL #1: QE reviews/edits/approves the draft.
HITL #2: QE verifies vendor evidence and re-approves; on pass the CAPA closes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.data.repository import CapaStore, get_capa_store
from app.models import CapaDraft, CapaStatus
from app.schemas import ActorNote, VerifyRequest

router = APIRouter(prefix="/capas", tags=["capas"])


def _get_or_404(store: CapaStore, capa_id: str) -> CapaDraft:
    capa = store.get(capa_id)
    if capa is None:
        raise HTTPException(status_code=404, detail=f"CAPA {capa_id} not found")
    return capa


def _transition(capa: CapaDraft, new_status: CapaStatus, event: str, note: str | None) -> None:
    capa.status = new_status
    capa.history.append({"event": event, "status": new_status.value, "note": note})


@router.get("", response_model=list[CapaDraft])
def list_capas(store: CapaStore = Depends(get_capa_store)) -> list[CapaDraft]:
    return store.list()


@router.get("/{capa_id}", response_model=CapaDraft)
def get_capa(capa_id: str, store: CapaStore = Depends(get_capa_store)) -> CapaDraft:
    return _get_or_404(store, capa_id)


@router.put("/{capa_id}", response_model=CapaDraft)
def edit_capa(
    capa_id: str, edited: CapaDraft, store: CapaStore = Depends(get_capa_store)
) -> CapaDraft:
    """QE edits the draft before approval (HITL #1). Id/report_id are preserved."""
    capa = _get_or_404(store, capa_id)
    if capa.status not in {CapaStatus.DRAFT, CapaStatus.ESCALATED}:
        raise HTTPException(status_code=409, detail="Only draft/escalated CAPAs are editable")
    edited.id, edited.report_id = capa.id, capa.report_id
    edited.status, edited.history = capa.status, capa.history
    edited.history.append({"event": "edited", "status": edited.status.value})
    return store.save(edited)


@router.post("/{capa_id}/approve", response_model=CapaDraft)
def approve(
    capa_id: str, body: ActorNote | None = None, store: CapaStore = Depends(get_capa_store)
) -> CapaDraft:
    """HITL #1: approve the draft; vendor begins implementation."""
    capa = _get_or_404(store, capa_id)
    if capa.status not in {CapaStatus.DRAFT, CapaStatus.ESCALATED}:
        raise HTTPException(status_code=409, detail="CAPA is not awaiting HITL #1")
    note = body.note if body else None
    _transition(capa, CapaStatus.APPROVED_HITL1, "hitl1_approved", note)
    _transition(capa, CapaStatus.VENDOR_IMPLEMENTING, "vendor_started", None)
    return store.save(capa)


@router.post("/{capa_id}/reject", response_model=CapaDraft)
def reject(
    capa_id: str, body: ActorNote | None = None, store: CapaStore = Depends(get_capa_store)
) -> CapaDraft:
    capa = _get_or_404(store, capa_id)
    _transition(capa, CapaStatus.REJECTED, "rejected", body.note if body else None)
    return store.save(capa)


@router.post("/{capa_id}/submit-evidence", response_model=CapaDraft)
def submit_evidence(
    capa_id: str, body: ActorNote | None = None, store: CapaStore = Depends(get_capa_store)
) -> CapaDraft:
    """Vendor submits evidence of effectiveness; awaits HITL #2."""
    capa = _get_or_404(store, capa_id)
    if capa.status != CapaStatus.VENDOR_IMPLEMENTING:
        raise HTTPException(status_code=409, detail="CAPA is not in vendor implementation")
    _transition(capa, CapaStatus.VERIFYING, "evidence_submitted", body.note if body else None)
    return store.save(capa)


@router.post("/{capa_id}/verify", response_model=CapaDraft)
def verify(
    capa_id: str, body: VerifyRequest, store: CapaStore = Depends(get_capa_store)
) -> CapaDraft:
    """HITL #2: verify effectiveness. On pass -> close; on fail -> back to vendor."""
    capa = _get_or_404(store, capa_id)
    if capa.status != CapaStatus.VERIFYING:
        raise HTTPException(status_code=409, detail="CAPA is not awaiting HITL #2")
    if body.passed:
        _transition(capa, CapaStatus.APPROVED_HITL2, "hitl2_approved", body.note)
        _transition(capa, CapaStatus.CLOSED, "closed_written_back", None)
    else:
        _transition(capa, CapaStatus.VENDOR_IMPLEMENTING, "hitl2_rework", body.note)
    return store.save(capa)
