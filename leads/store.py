"""Reading and writing leads in Supabase."""
from datetime import datetime, timezone

from leads.models import Enrichment, InboundLead, Place, WaitlistSignup


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LeadStore:
    def __init__(self, db):
        self.db = db

    def existing(self, place_ids: list[str]) -> dict[str, bool]:
        """Which of these place_ids are already saved? Returns {place_id: already_enriched}."""
        if not place_ids:
            return {}
        rows = self.db.table("leads").select("place_id, enrichment").in_("place_id", place_ids).execute().data
        return {r["place_id"]: r.get("enrichment") is not None for r in rows}

    def save_place(self, place: Place, *, category: str, city: str, website_status: str, score: int,
                   score_reason: str, score_breakdown: dict, enrichment: Enrichment | None) -> None:
        """Insert, or update if this place_id is already saved ("upsert").

        We never send `status` or `created_at`, so a rerun keeps your pipeline
        progress (e.g. 'contacted') and the original date. Enrichment is only sent
        when we have a new one, so an old enrichment is never wiped.
        """
        row = {
            "place_id": place.id,
            "source": "places",
            "business_name": place.name,
            "category": category,
            "primary_type": place.primary_type,
            "city": city,
            "address": place.address,
            "phone": place.phone,
            "website_uri": place.website_uri,
            "website_status": website_status,
            "rating": place.rating,
            "user_rating_count": place.user_rating_count,
            "opening_hours": place.opening_hours,
            "google_maps_uri": place.google_maps_uri,
            "photos": place.photos,
            "score": score,
            "score_reason": score_reason,
            "score_breakdown": score_breakdown,
            "updated_at": now(),
        }
        if enrichment is not None:
            row["enrichment"] = enrichment.model_dump()
            row["enriched_at"] = now()
        self.db.table("leads").upsert(row, on_conflict="place_id").execute()

    def save_inbound(self, lead: InboundLead) -> bool:
        """Save a website form request. Returns False if the same email+business already asked."""
        dupes = (
            self.db.table("leads").select("id, business_name").eq("source", "inbound").eq("email", lead.email)
            .execute().data
        )
        if any(d["business_name"].lower() == lead.business_name.lower() for d in dupes):
            return False
        self.db.table("leads").insert({
            "source": "inbound",
            "business_name": lead.business_name,
            "city": lead.city,
            "phone": lead.phone,
            "email": lead.email,
            "google_maps_uri": lead.google_maps_url,
        }).execute()
        return True

    def save_waitlist(self, signup: WaitlistSignup) -> None:
        # Upsert on email: signing up twice just updates the details.
        self.db.table("waitlist").upsert({
            "name": signup.name, "email": signup.email,
            "linkedin_url": signup.linkedin_url, "source": signup.source,
        }, on_conflict="email").execute()
