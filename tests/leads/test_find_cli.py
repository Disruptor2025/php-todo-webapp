import httpx

from leads import find
from leads.places import PlacesClient
from tests.fakes import FakeClaude, FakePlacesAPI, place_json

ARGS = ["--city", "Austin, TX", "--categories", "plumber", "--limit", "20", "--enrich-top", "1"]


def places_client(api):
    return PlacesClient("k", http=httpx.Client(transport=api.transport), sleep=lambda s: None)


def test_first_run_asks_for_approval_and_spends_nothing(db, capsys):
    api, claude = FakePlacesAPI({}), FakeClaude()
    code = find.main(ARGS, db=db, places=places_client(api), claude=claude)
    assert code == find.EXIT_WAITING
    out = capsys.readouterr().out
    assert "Needs approval" in out and "Approval id" in out
    assert db.rows("approvals")[0]["status"] == "pending"
    assert db.rows("approvals")[0]["estimated_cost_usd"] > 0
    assert api.calls == [] and claude.calls == []


def test_runs_after_approval_and_prints_table(db, capsys):
    find.main(ARGS, db=db, places=places_client(FakePlacesAPI({})), claude=FakeClaude())
    db.table("approvals").update({"status": "approved"}).execute()
    api = FakePlacesAPI({"plumber in Austin, TX": [place_json(1, displayName={"text": "Joe's Plumbing"})]})
    code = find.main(ARGS, db=db, places=places_client(api), claude=FakeClaude())
    assert code == 0
    out = capsys.readouterr().out
    assert "Joe's Plumbing" in out and "Score" in out
    assert db.rows("approvals")[0]["status"] == "used"


def test_wait_polls_until_rejected(db, capsys):
    sleeps = []

    def fake_sleep(s):
        sleeps.append(s)
        db.table("approvals").update({"status": "rejected"}).execute()  # you click Reject

    code = find.main(ARGS + ["--wait"], db=db, places=places_client(FakePlacesAPI({})), claude=FakeClaude(),
                     sleep=fake_sleep)
    assert code == 1 and sleeps
    assert "rejected" in capsys.readouterr().out


def test_table_shows_top_n():
    leads = [{"name": f"B{i}", "category": "plumber", "score": 90 - i, "rating": 4.5, "reviews": 10,
              "phone": "1", "website_status": "none", "enriched": False} for i in range(30)]
    table = find.format_table(leads, 20)
    assert len(table.splitlines()) == 22  # header + rule + 20 rows
