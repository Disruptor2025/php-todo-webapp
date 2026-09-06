from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/lanes", tags=["lanes"])


@router.get("", response_model=list[schemas.LaneRateOut])
def list_lanes(db: Session = Depends(get_db)):
    return db.query(models.LaneRate).order_by(models.LaneRate.origin).all()
