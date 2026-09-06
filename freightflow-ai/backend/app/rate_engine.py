"""
Dynamic margin & rate engine.

Cross-references a parsed tender's lane/equipment against historical lane
rate data (loaded into a Pandas DataFrame from SQLite), applies the current
fuel surcharge, and computes a recommended broker quote + estimated margin.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from . import models

DEFAULT_MILES_PER_LANE = 800  # used only if no mileage data exists for a lane
NATIONAL_AVG_RATE_PER_MILE = 2.35
DEFAULT_TARGET_MARGIN = 0.14


@dataclass
class RateQuote:
    miles: float
    carrier_cost_estimate: float
    fuel_surcharge_amount: float
    recommended_rate: float
    estimated_profit: float
    estimated_margin_pct: float
    lane_match_type: str  # exact | equipment_avg | national_avg


def _normalize(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _load_lane_rates_df(db: Session) -> pd.DataFrame:
    rows = db.query(models.LaneRate).all()
    records = [
        {
            "origin": _normalize(r.origin),
            "destination": _normalize(r.destination),
            "equipment_type": _normalize(r.equipment_type),
            "miles": r.miles,
            "avg_rate_per_mile": r.avg_rate_per_mile,
            "sample_count": r.sample_count,
        }
        for r in rows
    ]
    return pd.DataFrame.from_records(
        records,
        columns=["origin", "destination", "equipment_type", "miles", "avg_rate_per_mile", "sample_count"],
    )


def _latest_fuel_surcharge_pct(db: Session) -> float:
    row = (
        db.query(models.FuelSurcharge)
        .order_by(models.FuelSurcharge.effective_date.desc())
        .first()
    )
    return row.surcharge_pct if row else 0.18


def _target_margin_pct(db: Session, equipment_type: Optional[str]) -> float:
    if not equipment_type:
        return DEFAULT_TARGET_MARGIN
    row = (
        db.query(models.CarrierMargin)
        .filter(models.CarrierMargin.equipment_type == equipment_type)
        .first()
    )
    return row.target_margin_pct if row else DEFAULT_TARGET_MARGIN


def compute_quote(
    db: Session,
    origin: Optional[str],
    destination: Optional[str],
    equipment_type: Optional[str],
    weight_lbs: Optional[float] = None,
) -> RateQuote:
    df = _load_lane_rates_df(db)
    o, d, eq = _normalize(origin), _normalize(destination), _normalize(equipment_type)

    lane_match_type = "national_avg"
    miles = DEFAULT_MILES_PER_LANE
    rate_per_mile = NATIONAL_AVG_RATE_PER_MILE

    if not df.empty:
        exact = df[(df.origin == o) & (df.destination == d) & (df.equipment_type == eq)]
        if not exact.empty:
            weighted = (exact["avg_rate_per_mile"] * exact["sample_count"]).sum() / exact["sample_count"].sum()
            rate_per_mile = float(weighted)
            miles = float(exact["miles"].mean())
            lane_match_type = "exact"
        else:
            eq_match = df[df.equipment_type == eq] if eq else pd.DataFrame()
            if not eq_match.empty:
                weighted = (eq_match["avg_rate_per_mile"] * eq_match["sample_count"]).sum() / eq_match[
                    "sample_count"
                ].sum()
                rate_per_mile = float(weighted)
                miles = float(eq_match["miles"].mean())
                lane_match_type = "equipment_avg"

    linehaul = rate_per_mile * miles

    # Modest weight-based adjustment: heavier loads trend toward higher linehaul cost.
    if weight_lbs and weight_lbs > 42000:
        linehaul *= 1.05

    fuel_pct = _latest_fuel_surcharge_pct(db)
    fuel_surcharge_amount = linehaul * fuel_pct
    carrier_cost_estimate = linehaul + fuel_surcharge_amount

    target_margin = _target_margin_pct(db, equipment_type)
    recommended_rate = carrier_cost_estimate / (1 - target_margin)
    estimated_profit = recommended_rate - carrier_cost_estimate
    estimated_margin_pct = estimated_profit / recommended_rate if recommended_rate else 0.0

    return RateQuote(
        miles=round(miles, 1),
        carrier_cost_estimate=round(carrier_cost_estimate, 2),
        fuel_surcharge_amount=round(fuel_surcharge_amount, 2),
        recommended_rate=round(recommended_rate, 2),
        estimated_profit=round(estimated_profit, 2),
        estimated_margin_pct=round(estimated_margin_pct, 4),
        lane_match_type=lane_match_type,
    )
