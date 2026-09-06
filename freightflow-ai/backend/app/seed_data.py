"""Seeds the database with sample historical lane rates, fuel surcharge, and
target carrier margins so the rate engine has data to cross-reference on
first run."""
from datetime import date

from .database import SessionLocal, engine, Base
from . import models

SAMPLE_LANES = [
    # origin, destination, equipment, miles, avg_rate_per_mile, sample_count
    ("Dallas, TX", "Atlanta, GA", "Dry Van", 780, 2.45, 42),
    ("Atlanta, GA", "Dallas, TX", "Dry Van", 780, 2.15, 35),
    ("Los Angeles, CA", "Phoenix, AZ", "Dry Van", 370, 2.80, 51),
    ("Chicago, IL", "Detroit, MI", "Dry Van", 280, 2.60, 60),
    ("Chicago, IL", "New York, NY", "Reefer", 790, 3.10, 28),
    ("Miami, FL", "Charlotte, NC", "Reefer", 650, 2.95, 22),
    ("Houston, TX", "Memphis, TN", "Flatbed", 570, 2.70, 19),
    ("Denver, CO", "Salt Lake City, UT", "Flatbed", 525, 2.55, 15),
    ("Seattle, WA", "Portland, OR", "Dry Van", 175, 3.20, 33),
    ("Newark, NJ", "Boston, MA", "Dry Van", 225, 3.05, 40),
    ("Dallas, TX", "Houston, TX", "Dry Van", 240, 2.90, 55),
    ("Atlanta, GA", "Orlando, FL", "Reefer", 440, 2.75, 24),
    ("Kansas City, MO", "St. Louis, MO", "Flatbed", 250, 2.65, 12),
    ("Columbus, OH", "Pittsburgh, PA", "Dry Van", 185, 2.85, 27),
    ("Phoenix, AZ", "Las Vegas, NV", "Power Only", 300, 2.50, 10),
]

CARRIER_MARGINS = [
    ("Dry Van", 0.13),
    ("Reefer", 0.16),
    ("Flatbed", 0.15),
    ("Step Deck", 0.15),
    ("Power Only", 0.12),
    ("Box Truck", 0.14),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.LaneRate).count() == 0:
            for origin, dest, equip, miles, rate, samples in SAMPLE_LANES:
                db.add(
                    models.LaneRate(
                        origin=origin,
                        destination=dest,
                        equipment_type=equip,
                        miles=miles,
                        avg_rate_per_mile=rate,
                        sample_count=samples,
                    )
                )

        if db.query(models.FuelSurcharge).count() == 0:
            db.add(models.FuelSurcharge(effective_date=str(date.today()), surcharge_pct=0.18))

        if db.query(models.CarrierMargin).count() == 0:
            for equip, margin in CARRIER_MARGINS:
                db.add(models.CarrierMargin(equipment_type=equip, target_margin_pct=margin))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed data loaded.")
