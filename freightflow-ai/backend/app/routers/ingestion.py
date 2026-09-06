from datetime import datetime

import pdfplumber
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


@router.post("/email", response_model=schemas.TenderOut)
def ingest_email(payload: schemas.EmailIngestRequest, db: Session = Depends(get_db)):
    """Simulated inbound-email webhook: accepts raw unstructured tender text."""
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text must not be empty")

    tender = models.Tender(
        source=models.SourceType.EMAIL,
        filename=payload.filename,
        raw_text=payload.raw_text,
        status=models.TenderStatus.INCOMING,
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return tender


@router.post("/document", response_model=schemas.TenderOut)
async def ingest_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Simulated document webhook: accepts an uploaded PDF (BOL / rate con / load tender)."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    contents = await file.read()
    text_parts = []
    try:
        import io

        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}")

    raw_text = "\n".join(text_parts).strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="No extractable text found in PDF")

    tender = models.Tender(
        source=models.SourceType.PDF,
        filename=file.filename,
        raw_text=raw_text,
        status=models.TenderStatus.INCOMING,
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return tender
