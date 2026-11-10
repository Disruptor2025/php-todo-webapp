"""End-to-end run with fake Google, fake Claude and fake Supabase."""
import httpx
import pytest

from leads.dnc import DncList
from leads.enrich import Enricher
from leads.pipeline import KIND, FindRequest, run
from leads.places import PlacesClient
from leads.store import LeadStore
from shared.approvals import ApprovalError, Approvals
from tests.fakes import FakeClaude, FakePlacesAPI, place_json

CITY = "Austin, TX"


def search_results():
    return {
        f"plumber in {CITY}": [
            place_json(1, userRatingCount=300, rating=4.9),                         # no website: best lead
            place_json(2, websiteUri="https://www.facebook.com/biz2"),             # social only
            place_json(3, websiteUri="https://realplumbing.com"),                  # has a site: skip
            place_json(4, nationalPhoneNumber=None),                               # no phone: skip
            place_json(5, userRatingCount=2, rating=3.2, regularOpeningHours=None),  # weak lead
        ],
        f"salon in {CITY}": [
            place_json(1),                                                         # duplicate of plumber 1
            place_json(6, primaryType="hair_salon", nationalPhoneNumber="(512) 555-9999"),
        ],
    }


class Env:
    """Everything a run needs, wired to fakes."""

    def __init__(self, db, enrich_top=2, dnc_rows=(), claude=None):
        self.db = db
        self.api = FakePlacesAPI(search_results())
        self.claude = claude or FakeClaude()
        self.req = FindRequest(CITY, ["plumber", "salon"], limit=20, enrich_top=enrich_top)
        self.approvals = Approvals(db)
        if dnc_rows:
            db.table("dnc").insert(list(dnc_rows)).execute()

    def approve(self):
        a = self.approvals.request(KIND, self.req.describe(), 1.0, self.req.payload())
        self.db.table("approvals").update({"status": "approved"}).eq("id", a.id).execute()
        return a.id

    def run(self, approval_id=None):
        places = PlacesClient("k", http=httpx.Client(transport=self.api.transport), sleep=lambda s: None)
        return run(self.req, approval_id=approval_id or self.approve(), approvals=self.approvals, places=places,
                   enricher=Enricher(self.claude, "claude-opus-5-5"), store=LeadStore(self.db),
                   dnc=DncList.load(self.db))


def saved(db):
    return {r["place_id"]: r for r in db.rows("leads")}


def test_filters_scores_and_saves(db):
    report = Env(db).run()
    leads = saved(db)
    assert set(leads) == {"place-1", "place-2", "place-5", "place-6"}
    assert leads["place-1"]["website_status"] == "none"
    assert leads["place-2"]["website_status"] == "social_only"
    assert report.skipped_has_website == 1 and report.skipped_no_phone == 1
    assert report.fetched == 7 and report.unique == 6  # place-1 found twice
    # Best first, with the reason stored.
    assert report.leads[0]["place_id"] == "place-1"
    assert leads["place-1"]["score"] > leads["place-5"]["score"]
    assert "Reviews: 300 reviews" in leads["place-1"]["score_reason"]
    assert leads["place-1"]["score_breakdown"]["category"]["why"] == "home services"
    assert all(r["status"] == "new" for r in leads.values())


def test_keeps_all_places_fields(db):
    Env(db).run()
    r = saved(db)["place-1"]
    for col in ["business_name", "address", "phone", "rating", "user_rating_count", "opening_hours",
                "primary_type", "google_maps_uri", "photos", "category", "city"]:
        assert r[col] not in (None, ""), col


def test_enriches_only_top_n(db):
    env = Env(db, enrich_top=2)
    report = env.run()
    enriched = {pid for pid, r in saved(db).items() if r.get("enrichment")}
    top_two = {l["place_id"] for l in report.leads[:2]}
    assert enriched == top_two
    assert len(env.claude.calls) == 2 and report.enriched == 2


def test_rerun_does_not_duplicate_or_reset_progress(db):
    env = Env(db, enrich_top=2)
    env.run()
    # You contact the best lead between runs.
    db.table("leads").update({"status": "contacted"}).eq("place_id", "place-1").execute()
    calls_after_first = len(env.claude.calls)

    report = env.run()
    leads = db.rows("leads")
    assert len(leads) == 4                               # no duplicates
    assert report.saved_new == 0 and report.updated_existing == 4
    assert saved(db)["place-1"]["status"] == "contacted"  # progress kept
    assert saved(db)["place-1"]["enrichment"] is not None  # enrichment kept
    assert len(env.claude.calls) == calls_after_first     # no paying twice for enrichment


def test_dnc_by_place_id_and_phone_excluded(db):
    report = Env(db, dnc_rows=[{"place_id": "place-1"}, {"phone": "+1 512 555 9999"}]).run()
    assert set(saved(db)) == {"place-2", "place-5"}
    assert report.skipped_dnc == 2


def test_refuses_to_run_without_approval(db):
    env = Env(db)
    pending = env.approvals.request(KIND, "x", 1.0, env.req.payload())
    with pytest.raises(ApprovalError):
        env.run(approval_id=pending.id)
    assert env.api.calls == [] and env.claude.calls == []  # nothing spent
    assert db.rows("leads") == []


def test_places_requests_stay_within_plan(db):
    env = Env(db)
    report = env.run()
    assert report.places_requests <= env.req.max_places_requests()


def test_request_normalizes_and_splits_limit():
    a = FindRequest(" Austin,  TX ", ["Salon", "plumber ", "salon"], limit=100)
    b = FindRequest("Austin, TX", ["plumber", "salon"], limit=100)
    assert a.payload() == b.payload()
    assert FindRequest("X", ["a", "b", "c"], limit=100).per_category() == {"a": 34, "b": 33, "c": 33}
    assert FindRequest("X", ["a"], limit=500).per_category() == {"a": 60}  # Google's cap
    with pytest.raises(ValueError):
        FindRequest("X", [" "], limit=10)


def test_cost_estimate():
    req = FindRequest("X", ["a", "b"], limit=100, enrich_top=20)  # 50 each -> 3 requests each
    assert req.max_places_requests() == 6
    assert req.estimated_cost(0.035, 0.03) == pytest.approx(6 * 0.035 + 40 * 0.03)
