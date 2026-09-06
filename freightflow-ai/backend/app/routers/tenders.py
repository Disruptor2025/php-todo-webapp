from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..parser import parse_tender_text
from ..rate_engine import compute_quote
from ..quote_generator import build_email_draft, build_rate_confirmation_html, build_rate_confirmation_pdf

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


def _generate_quote_artifacts(db: Session, tender: models.Tender, final_rate: float) -> models.Quote:
    email_draft = build_email_draft(tender, final_rate)
    html = build_rate_confirmation_html(tender, final_rate)
    pdf_path = build_rate_confirmation_pdf(tender, final_rate)

    quote = models.Quote(
        tender_id=tender.id,
        email_draft=email_draft,
        rate_confirmation_html=html,
        pdf_path=pdf_path,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("", response_model=list[schemas.TenderOut])
def list_tenders(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Tender)
    if status:
        q = q.filter(models.Tender.status == status)
    return q.order_by(models.Tender.created_at.desc()).all()


@router.get("/{tender_id}", response_model=schemas.TenderOut)
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.post("/{tender_id}/process", response_model=schemas.TenderOut)
def process_tender(tender_id: int, db: Session = Depends(get_db)):
    """Runs AI parsing + the margin/rate engine on a raw incoming tender,
    then auto-generates a client-ready quote draft."""
    tender = db.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    parsed = parse_tender_text(tender.raw_text)
    tender.origin = parsed.origin
    tender.destination = parsed.destination
    tender.equipment_type = parsed.equipment_type
    tender.weight_lbs = parsed.weight_lbs
    tender.pickup_date = parsed.pickup_date
    tender.commodity = parsed.commodity
    tender.parse_confidence = parsed.confidence
    tender.parser_used = parsed.parser_used
    tender.parsed_at = datetime.utcnow()

    quote = compute_quote(db, parsed.origin, parsed.destination, parsed.equipment_type, parsed.weight_lbs)
    tender.miles = quote.miles
    tender.carrier_cost_estimate = quote.carrier_cost_estimate
    tender.fuel_surcharge_amount = quote.fuel_surcharge_amount
    tender.recommended_rate = quote.recommended_rate
    tender.estimated_profit = quote.estimated_profit
    tender.estimated_margin_pct = quote.estimated_margin_pct
    tender.lane_match_type = quote.lane_match_type

    tender.status = models.TenderStatus.PARSED_QUOTED

    db.commit()
    db.refresh(tender)

    _generate_quote_artifacts(db, tender, tender.recommended_rate)

    return tender


@router.post("/{tender_id}/decision", response_model=schemas.TenderOut)
def decide_tender(tender_id: int, payload: schemas.DecisionRequest, db: Session = Depends(get_db)):
    """Broker approves the AI-generated quote as-is, or overrides the rate."""
    tender = db.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.status != models.TenderStatus.PARSED_QUOTED:
        raise HTTPException(status_code=400, detail="Tender must be in parsed_quoted status to decide")

    if payload.action == "approve":
        tender.final_rate = tender.recommended_rate
        tender.decision = "approved"
    elif payload.action == "override":
        if payload.override_rate is None:
            raise HTTPException(status_code=400, detail="override_rate is required for override action")
        tender.final_rate = payload.override_rate
        tender.decision = "overridden"
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'override'")

    tender.decision_note = payload.note
    tender.decided_at = datetime.utcnow()
    tender.status = models.TenderStatus.ACTIVE

    db.commit()
    db.refresh(tender)

    _generate_quote_artifacts(db, tender, tender.final_rate)

    return tender


@router.post("/{tender_id}/audit", response_model=schemas.TenderOut)
def audit_tender(tender_id: int, db: Session = Depends(get_db)):
    """Marks an active load as audited/completed with a full document trail."""
    tender = db.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.status != models.TenderStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Tender must be active to audit")

    tender.status = models.TenderStatus.AUDITED
    db.commit()
    db.refresh(tender)
    return tender


@router.get("/{tender_id}/quote", response_model=schemas.QuoteOut)
def get_latest_quote(tender_id: int, db: Session = Depends(get_db)):
    quote = (
        db.query(models.Quote)
        .filter(models.Quote.tender_id == tender_id)
        .order_by(models.Quote.created_at.desc())
        .first()
    )
    if not quote:
        raise HTTPException(status_code=404, detail="No quote generated yet for this tender")
    return quote


@router.get("/{tender_id}/pdf")
def get_rate_confirmation_pdf(tender_id: int, db: Session = Depends(get_db)):
    quote = (
        db.query(models.Quote)
        .filter(models.Quote.tender_id == tender_id)
        .order_by(models.Quote.created_at.desc())
        .first()
    )
    if not quote or not quote.pdf_path:
        raise HTTPException(status_code=404, detail="No rate confirmation PDF generated yet")
    return FileResponse(
        quote.pdf_path,
        media_type="application/pdf",
        filename=f"rate_confirmation_tender_{tender_id}.pdf",
    )
