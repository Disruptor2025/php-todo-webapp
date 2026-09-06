import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Enum as SAEnum, ForeignKey
)
from sqlalchemy.orm import relationship

from .database import Base


class TenderStatus(str, enum.Enum):
    INCOMING = "incoming"          # raw doc/email just landed, not yet parsed
    PARSED_QUOTED = "parsed_quoted"  # AI parsed + quote computed, awaiting broker
    ACTIVE = "active"              # broker approved, load is live
    AUDITED = "audited"            # completed load with full document trail


class SourceType(str, enum.Enum):
    EMAIL = "email"
    PDF = "pdf"


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(SAEnum(SourceType), default=SourceType.EMAIL, nullable=False)
    filename = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)
    status = Column(SAEnum(TenderStatus), default=TenderStatus.INCOMING, nullable=False, index=True)

    # Parsed fields
    origin = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    equipment_type = Column(String, nullable=True)
    weight_lbs = Column(Float, nullable=True)
    pickup_date = Column(String, nullable=True)
    commodity = Column(String, nullable=True)
    miles = Column(Float, nullable=True)
    parse_confidence = Column(Float, nullable=True)
    parser_used = Column(String, nullable=True)

    # Rate engine outputs
    carrier_cost_estimate = Column(Float, nullable=True)
    fuel_surcharge_amount = Column(Float, nullable=True)
    recommended_rate = Column(Float, nullable=True)
    estimated_margin_pct = Column(Float, nullable=True)
    estimated_profit = Column(Float, nullable=True)
    lane_match_type = Column(String, nullable=True)  # exact | equipment_avg | national_avg

    # Broker decision
    final_rate = Column(Float, nullable=True)
    decision = Column(String, nullable=True)  # approved | overridden
    decision_note = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    parsed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    quotes = relationship("Quote", back_populates="tender", cascade="all, delete-orphan")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    email_draft = Column(Text, nullable=True)
    rate_confirmation_html = Column(Text, nullable=True)
    pdf_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tender = relationship("Tender", back_populates="quotes")


class LaneRate(Base):
    """Historical lane rate data used by the margin/rate engine."""
    __tablename__ = "lane_rates"

    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String, nullable=False, index=True)
    destination = Column(String, nullable=False, index=True)
    equipment_type = Column(String, nullable=False, index=True)
    miles = Column(Float, nullable=False)
    avg_rate_per_mile = Column(Float, nullable=False)
    sample_count = Column(Integer, default=1)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class FuelSurcharge(Base):
    """Simulated national average fuel surcharge, % applied on top of linehaul."""
    __tablename__ = "fuel_surcharges"

    id = Column(Integer, primary_key=True, index=True)
    effective_date = Column(String, nullable=False)
    surcharge_pct = Column(Float, nullable=False)  # e.g. 0.18 == 18%


class CarrierMargin(Base):
    """Target broker margin percentage by equipment type."""
    __tablename__ = "carrier_margins"

    id = Column(Integer, primary_key=True, index=True)
    equipment_type = Column(String, nullable=False, unique=True)
    target_margin_pct = Column(Float, nullable=False)  # e.g. 0.15 == 15%
