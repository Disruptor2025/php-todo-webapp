"""Data shapes used by the leads module (Pydantic validates them for us)."""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

LEAD_STATUSES = ("new", "demo_built", "contacted", "replied", "won", "lost")


class Place(BaseModel):
    """One business from Google Places, keeping only the fields we asked for."""
    id: str
    name: str
    address: str | None = None
    phone: str | None = None
    website_uri: str | None = None
    rating: float | None = None
    user_rating_count: int = 0
    opening_hours: dict | None = None
    primary_type: str | None = None
    google_maps_uri: str | None = None
    photos: list[dict] = []

    @classmethod
    def from_api(cls, p: dict) -> "Place":
        """Convert Google's JSON (camelCase, nested) into our flat model."""
        return cls(
            id=p["id"],
            name=(p.get("displayName") or {}).get("text", ""),
            address=p.get("formattedAddress"),
            phone=p.get("nationalPhoneNumber"),
            website_uri=p.get("websiteUri"),
            rating=p.get("rating"),
            user_rating_count=p.get("userRatingCount") or 0,
            opening_hours=p.get("regularOpeningHours"),
            primary_type=p.get("primaryType"),
            google_maps_uri=p.get("googleMapsUri"),
            # Keep only photo references (max 5); downloading photos costs extra.
            photos=[
                {"name": ph.get("name"), "width": ph.get("widthPx"), "height": ph.get("heightPx"),
                 "attributions": ph.get("authorAttributions", [])}
                for ph in (p.get("photos") or [])[:5]
            ],
        )


class Enrichment(BaseModel):
    """What we ask Claude to produce for a lead. Validated before saving."""
    summary: str = Field(description="One sentence describing the business", max_length=300)
    services: list[str] = Field(description="Services the business likely offers", min_length=1, max_length=12)
    site_sections: list[str] = Field(description="Suggested sections for their website", min_length=3, max_length=10)
    selling_points: list[str] = Field(description="Exactly 3 reasons this business would benefit from Prezence",
                                      min_length=3, max_length=3)
    tone: Literal["friendly", "premium", "family-run"]


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InboundLead(BaseModel):
    """The website's free preview form."""
    business_name: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=80)
    phone: str = Field(min_length=3, max_length=30)
    email: str = Field(max_length=160)
    google_maps_url: str | None = Field(default=None, max_length=500)
    source: str = Field(default="website_preview_form", max_length=50)
    website: str | None = None  # hidden spam trap: real people leave it empty

    @field_validator("business_name", "city", "phone", "email", mode="before")
    @classmethod
    def strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError("not a valid email address")
        return v.lower()

    @field_validator("google_maps_url", mode="before")
    @classmethod
    def valid_url(cls, v):
        if not v or not str(v).strip():
            return None
        v = str(v).strip()
        if not v.startswith(("https://", "http://")):
            raise ValueError("must be a link starting with https://")
        return v


class WaitlistSignup(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=160)
    linkedin_url: str | None = Field(default=None, max_length=300)
    source: str = Field(default="founders_waitlist", max_length=50)
    website: str | None = None  # spam trap

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip()
        if not EMAIL_RE.match(v):
            raise ValueError("not a valid email address")
        return v.lower()
