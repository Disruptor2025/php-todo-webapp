import pytest
from fastapi.testclient import TestClient

from leads.api import app, get_db_dep

FORM = {"business_name": "Test Bakery", "city": "Elmsworth", "phone": "512-555-0100",
        "email": "Owner@Test.example", "google_maps_url": "https://maps.app.goo.gl/abc",
        "source": "website_preview_form"}


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db_dep] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_inbound_creates_lead(client, db):
    res = client.post("/leads/inbound", json=FORM)
    assert res.status_code == 200 and res.json() == {"ok": True}
    [lead] = db.rows("leads")
    assert lead["source"] == "inbound" and lead["status"] == "new"
    assert lead["email"] == "owner@test.example"
    assert lead["google_maps_uri"] == FORM["google_maps_url"]
    assert lead.get("place_id") is None


def test_inbound_same_request_twice_not_duplicated(client, db):
    client.post("/leads/inbound", json=FORM)
    client.post("/leads/inbound", json=FORM)
    assert len(db.rows("leads")) == 1


def test_inbound_validates_fields(client, db):
    res = client.post("/leads/inbound", json={**FORM, "email": "not-an-email", "city": ""})
    assert res.status_code == 422
    assert set(res.json()["fields"]) == {"email", "city"}
    assert db.rows("leads") == []


def test_inbound_maps_link_optional(client, db):
    res = client.post("/leads/inbound", json={**FORM, "google_maps_url": ""})
    assert res.status_code == 200 and db.rows("leads")[0]["google_maps_uri"] is None


def test_inbound_spam_trap_saves_nothing(client, db):
    res = client.post("/leads/inbound", json={**FORM, "website": "http://spam"})
    assert res.status_code == 200 and db.rows("leads") == []


def test_inbound_respects_dnc(client, db):
    db.table("dnc").insert({"email": "owner@test.example"}).execute()
    res = client.post("/leads/inbound", json=FORM)
    assert res.status_code == 200          # doesn't reveal the list
    assert db.rows("leads") == []


def test_inbound_plain_form_post_redirects_to_site(client, db):
    res = client.post("/leads/inbound", data=FORM, follow_redirects=False)
    assert res.status_code == 303 and res.headers["location"].endswith("/preview?sent=1")
    assert len(db.rows("leads")) == 1


def test_cors_allows_website(client):
    res = client.options("/leads/inbound", headers={"Origin": "http://localhost:4321",
                                                    "Access-Control-Request-Method": "POST",
                                                    "Access-Control-Request-Headers": "content-type"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:4321"


def test_waitlist_signup_upserts(client, db):
    body = {"name": "Ada", "email": "ada@test.example", "source": "founders_waitlist"}
    assert client.post("/leads/waitlist", json=body).status_code == 200
    client.post("/leads/waitlist", json={**body, "name": "Ada L."})
    [row] = db.rows("waitlist")
    assert row["name"] == "Ada L."
