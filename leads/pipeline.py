"""The lead-finding run: search → filter → do-not-contact → score → enrich → save.

It only runs with an approved approval for the exact same request (see shared/approvals.py),
because Google Places and Claude both cost money.
"""
import logging
from dataclasses import dataclass, field

from leads.dnc import DncList
from leads.enrich import Enricher
from leads.filters import website_status
from leads.places import MAX_PER_QUERY, PlacesClient, requests_needed
from leads.scoring import score_place
from leads.store import LeadStore
from shared.approvals import Approvals

log = logging.getLogger(__name__)
KIND = "leads.find"


@dataclass
class FindRequest:
    city: str
    categories: list[str]
    limit: int = 100
    enrich_top: int = 20

    def __post_init__(self):
        # Tidy input so "Plumber, salon" and "salon,plumber" count as the same request.
        self.city = " ".join(self.city.split())
        self.categories = sorted({c.strip().lower() for c in self.categories if c.strip()})
        if not self.city or not self.categories:
            raise ValueError("city and at least one category are required")
        if self.limit < 1 or self.enrich_top < 0:
            raise ValueError("limit must be >= 1 and enrich_top >= 0")

    def payload(self) -> dict:
        return {"city": self.city, "categories": self.categories, "limit": self.limit, "enrich_top": self.enrich_top}

    def per_category(self) -> dict[str, int]:
        """Split the limit across categories (e.g. 100 over 3 = 34, 33, 33), max 60 each (Google's cap)."""
        base, extra = divmod(self.limit, len(self.categories))
        return {c: min(MAX_PER_QUERY, base + (1 if i < extra else 0)) for i, c in enumerate(self.categories)}

    def max_places_requests(self) -> int:
        return sum(requests_needed(n) for n in self.per_category().values() if n > 0)

    def max_claude_calls(self) -> int:
        return self.enrich_top * 2  # worst case: every lead needs its one retry

    def estimated_cost(self, places_cost: float, enrich_cost: float) -> float:
        """Worst-case cost: every page fetched and every enrichment retried."""
        return self.max_places_requests() * places_cost + self.max_claude_calls() * enrich_cost

    def describe(self) -> str:
        return (f"Find leads: {', '.join(self.categories)} in {self.city}. Up to {self.limit} businesses "
                f"({self.max_places_requests()} Google Places requests), enrich top {self.enrich_top} with Claude "
                f"(up to {self.max_claude_calls()} calls incl. retries).")


@dataclass
class RunReport:
    fetched: int = 0
    unique: int = 0
    skipped_has_website: int = 0
    skipped_no_phone: int = 0
    skipped_dnc: int = 0
    saved_new: int = 0
    updated_existing: int = 0
    enriched: int = 0
    places_requests: int = 0
    claude_calls: int = 0
    leads: list[dict] = field(default_factory=list)  # all saved leads this run, best first


def run(req: FindRequest, *, approval_id: str, approvals: Approvals, places: PlacesClient,
        enricher: Enricher | None, store: LeadStore, dnc: DncList) -> RunReport:
    # 1. Check the approval BEFORE spending anything (raises if not approved).
    approvals.consume(approval_id, KIND, req.payload())
    report = RunReport()

    # 2. Search each category. The same business can show up under two categories,
    #    so we keep the first one we see (dedup by place id).
    found: dict[str, tuple] = {}
    for category, n in req.per_category().items():
        if n <= 0:
            continue
        results = places.search(f"{category} in {req.city}", n)
        report.fetched += len(results)
        for p in results:
            found.setdefault(p.id, (p, category))
    report.unique = len(found)
    report.places_requests = places.requests_made

    # 3. Filter and score.
    candidates = []
    for place, category in found.values():
        status = website_status(place.website_uri)
        if status is None:
            report.skipped_has_website += 1
            continue
        if dnc.blocks(place_id=place.id, phone=place.phone):
            report.skipped_dnc += 1
            continue
        if not place.phone:  # required: we can't sell to a business we can't call
            report.skipped_no_phone += 1
            continue
        score, reason, breakdown = score_place(place, category)
        candidates.append({"place": place, "category": category, "website_status": status,
                           "score": score, "score_reason": reason, "score_breakdown": breakdown})
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # 4. Enrich the top N with Claude, skipping any already enriched on an earlier run (saves money).
    existing = store.existing([c["place"].id for c in candidates])
    for c in candidates[: req.enrich_top]:
        c["enrichment"] = None
        if enricher and not existing.get(c["place"].id):
            c["enrichment"] = enricher.enrich(c["place"], c["category"], req.city, c["website_status"])
            report.enriched += c["enrichment"] is not None
    report.claude_calls = enricher.calls if enricher else 0

    # 5. Save. Upsert on place_id, so reruns update instead of duplicating.
    for c in candidates:
        place = c["place"]
        store.save_place(place, category=c["category"], city=req.city, website_status=c["website_status"],
                         score=c["score"], score_reason=c["score_reason"], score_breakdown=c["score_breakdown"],
                         enrichment=c.get("enrichment"))
        if place.id in existing:
            report.updated_existing += 1
        else:
            report.saved_new += 1
        report.leads.append({"place_id": place.id, "name": place.name, "category": c["category"],
                             "score": c["score"], "phone": place.phone, "rating": place.rating,
                             "reviews": place.user_rating_count, "website_status": c["website_status"],
                             "enriched": c.get("enrichment") is not None or existing.get(place.id, False)})
    return report
