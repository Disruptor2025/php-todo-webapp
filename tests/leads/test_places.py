import httpx
import pytest

from leads.places import FIELD_MASK, PlacesClient, PlacesError, requests_needed
from tests.fakes import FakePlacesAPI, place_json


def make_client(api, **kw):
    sleeps = []
    client = PlacesClient("test-key", http=httpx.Client(transport=api.transport), sleep=sleeps.append, **kw)
    return client, sleeps


def test_field_mask_includes_everything_we_need():
    for f in ["id", "displayName", "formattedAddress", "nationalPhoneNumber", "websiteUri", "rating",
              "userRatingCount", "regularOpeningHours", "primaryType", "googleMapsUri", "photos"]:
        assert f"places.{f}" in FIELD_MASK
    assert "nextPageToken" in FIELD_MASK


def test_sends_key_and_field_mask_headers():
    api = FakePlacesAPI({"plumber in Austin": [place_json(1)]})
    client, _ = make_client(api)
    client.search("plumber in Austin", 20)
    headers = api.calls[0]["headers"]
    assert headers["x-goog-api-key"] == "test-key"
    assert headers["x-goog-fieldmask"] == FIELD_MASK


def test_paginates_until_limit():
    api = FakePlacesAPI({"q": [place_json(i) for i in range(55)]})
    client, _ = make_client(api)
    places = client.search("q", 45)
    assert len(places) == 45
    assert len(api.calls) == 3  # 20 + 20 + 5
    assert api.calls[2]["body"]["pageSize"] == 5
    assert client.requests_made == 3


def test_stops_when_no_more_pages():
    api = FakePlacesAPI({"q": [place_json(i) for i in range(7)]})
    client, _ = make_client(api)
    assert len(client.search("q", 60)) == 7
    assert len(api.calls) == 1


def test_never_asks_for_more_than_60():
    api = FakePlacesAPI({"q": [place_json(i) for i in range(100)]})
    client, _ = make_client(api)
    assert len(client.search("q", 100)) == 60
    assert requests_needed(100) == 3


def test_parses_place_fields():
    api = FakePlacesAPI({"q": [place_json(1, websiteUri="https://facebook.com/biz")]})
    client, _ = make_client(api)
    p = client.search("q", 1)[0]
    assert (p.id, p.name, p.phone, p.website_uri) == ("place-1", "Business 1", "(512) 555-0001", "https://facebook.com/biz")
    assert p.rating == 4.5 and p.user_rating_count == 50 and p.primary_type == "plumber"
    assert p.photos[0]["name"] == "places/place-1/photos/a"


def test_retries_rate_limits_with_backoff():
    api = FakePlacesAPI({"q": [place_json(1)]}, fail_first=[429, 503])
    client, sleeps = make_client(api)
    assert len(client.search("q", 20)) == 1
    # Waits grow 1s, 2s... but Retry-After: 3 from the server wins when it's longer.
    assert sleeps == [3, 3]
    assert len(api.calls) == 3


def test_gives_up_after_max_retries():
    api = FakePlacesAPI({"q": []}, fail_first=[429] * 10)
    client, sleeps = make_client(api, max_retries=2)
    with pytest.raises(PlacesError, match="after 3 attempts"):
        client.search("q", 20)
    assert len(sleeps) == 2


def test_does_not_retry_bad_requests():
    api = FakePlacesAPI({"q": []}, fail_first=[403])
    client, sleeps = make_client(api)
    with pytest.raises(PlacesError, match="403"):
        client.search("q", 20)
    assert sleeps == [] and len(api.calls) == 1


def test_retries_network_errors():
    attempts = []

    def flaky(request):
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={"places": [place_json(1)]})

    client = PlacesClient("k", http=httpx.Client(transport=httpx.MockTransport(flaky)), sleep=lambda s: None)
    assert len(client.search("q", 20)) == 1
