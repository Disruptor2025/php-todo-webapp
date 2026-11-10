"""Google Places API (New) - Text Search.

Docs: https://developers.google.com/maps/documentation/places/web-service/text-search

Each request returns up to 20 places. Google allows up to 3 pages (60 results)
per search. Every request costs money, so callers pass a hard `max_results`.
"""
import logging
import math
import time

import httpx

from leads.models import Place

log = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PAGE_SIZE = 20          # Google's maximum per request
MAX_PER_QUERY = 60      # Google stops paging after 60 results

# Only the fields we need. Google bills by the fields you request, so keep this tight.
FIELDS = [
    "id", "displayName", "formattedAddress", "nationalPhoneNumber", "websiteUri",
    "rating", "userRatingCount", "regularOpeningHours", "primaryType", "googleMapsUri", "photos",
]
FIELD_MASK = ",".join(f"places.{f}" for f in FIELDS) + ",nextPageToken"

RETRY_STATUSES = {429, 500, 502, 503, 504}  # rate limited or temporary server problems


class PlacesError(Exception):
    pass


def requests_needed(max_results: int) -> int:
    """How many API calls a search for `max_results` can make (used for cost estimates)."""
    return math.ceil(min(max_results, MAX_PER_QUERY) / PAGE_SIZE)


class PlacesClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None, max_retries: int = 4,
                 sleep=time.sleep):
        self.api_key = api_key
        self.http = http or httpx.Client(timeout=30)
        self.max_retries = max_retries
        self.sleep = sleep            # swapped for a fake in tests, so tests don't actually wait
        self.requests_made = 0        # each one is billed by Google

    def _post(self, body: dict) -> dict:
        """POST with retries. Waits 1s, 2s, 4s, 8s... between attempts (exponential backoff)."""
        headers = {"X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": FIELD_MASK}
        for attempt in range(self.max_retries + 1):
            retry_after = None
            try:
                self.requests_made += 1
                res = self.http.post(SEARCH_URL, json=body, headers=headers)
            except httpx.TransportError as e:  # network hiccup
                error = f"network error: {e}"
            else:
                if res.status_code == 200:
                    return res.json()
                if res.status_code not in RETRY_STATUSES:
                    # 400/403 etc. won't fix themselves (bad key, API not enabled...), so stop now.
                    raise PlacesError(f"Places API error {res.status_code}: {res.text[:300]}")
                error = f"HTTP {res.status_code}"
                retry_after = res.headers.get("Retry-After")
            if attempt == self.max_retries:
                raise PlacesError(f"Places API failed after {attempt + 1} attempts ({error})")
            delay = 2 ** attempt
            if retry_after and retry_after.isdigit():
                delay = max(delay, int(retry_after))  # respect the server's "wait this long"
            log.warning("Places %s, retrying in %ss", error, delay)
            self.sleep(delay)
        raise AssertionError("unreachable")

    def search(self, query: str, max_results: int) -> list[Place]:
        """Search e.g. 'plumber in Austin, TX', following pages until max_results."""
        max_results = min(max_results, MAX_PER_QUERY)
        places: list[Place] = []
        page_token = None
        while len(places) < max_results:
            body = {"textQuery": query, "pageSize": min(PAGE_SIZE, max_results - len(places))}
            if page_token:
                body["pageToken"] = page_token
            data = self._post(body)
            places += [Place.from_api(p) for p in data.get("places", [])]
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return places[:max_results]
