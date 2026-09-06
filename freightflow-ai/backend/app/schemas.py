from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class EmailIngestRequest(BaseModel):
    raw_text: str
    filename: Optional[str] = None


class ParsedFields(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    equipment_type: Optional[str] = None
    weight_lbs: Optional[float] = None
    pickup_date: Optional[str] = None
    commodity: Optional[str] = None
    confidence: float = 0.0
    parser_used: str = "mock"


class TenderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    filename: Optional[str] = None
    raw_text: str
    status: str

    origin: Optional[str] = None
    destination: Optional[str] = None
    equipment_type: Optional[str] = None
    weight_lbs: Optional[float] = None
    pickup_date: Optional[str] = None
    commodity: Optional[str] = None
    miles: Optional[float] = None
    parse_confidence: Optional[float] = None
    parser_used: Optional[str] = None

    carrier_cost_estimate: Optional[float] = None
    fuel_surcharge_amount: Optional[float] = None
    recommended_rate: Optional[float] = None
    estimated_margin_pct: Optional[float] = None
    estimated_profit: Optional[float] = None
    lane_match_type: Optional[str] = None

    final_rate: Optional[float] = None
    decision: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None

    created_at: datetime
    parsed_at: Optional[datetime] = None
    updated_at: datetime


class DecisionRequest(BaseModel):
    action: str  # "approve" | "override" | "audit"
    override_rate: Optional[float] = None
    note: Optional[str] = None


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tender_id: int
    email_draft: Optional[str] = None
    rate_confirmation_html: Optional[str] = None
    pdf_path: Optional[str] = None
    created_at: datetime


class LaneRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origin: str
    destination: str
    equipment_type: str
    miles: float
    avg_rate_per_mile: float
    sample_count: int
