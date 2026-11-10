"""Fake versions of external services, so tests never touch the real ones.

FakeSupabase copies the small part of the supabase-py query API our code uses
(select/eq/in_/order/limit/insert/update/upsert/execute), storing rows in memory.
"""
import copy
import itertools
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

# Column defaults and unique columns that the real database (our SQL migrations) provides.
DEFAULTS = {"leads": {"status": "new", "source": "places"}}
UNIQUE = {"leads": ["place_id"], "waitlist": ["email"]}

_clock = itertools.count()  # makes created_at strictly increasing, so ordering is predictable


class FakeSupabase:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def table(self, name):
        return _Query(self, name)

    def rows(self, name):
        return self.tables.setdefault(name, [])


class _Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.filters, self.action, self.payload = [], "select", None
        self.order_by, self.limit_n, self.on_conflict = None, None, None

    # --- query builders (each returns self so calls can be chained) ---
    def select(self, *_cols):
        self.action = "select"
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        vals = list(vals)
        self.filters.append(lambda r: r.get(col) in vals)
        return self

    def order(self, col, desc=False):
        self.order_by = (col, desc)
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def insert(self, rows):
        self.action, self.payload = "insert", rows
        return self

    def update(self, values):
        self.action, self.payload = "update", values
        return self

    def upsert(self, rows, on_conflict=None):
        self.action, self.payload, self.on_conflict = "upsert", rows, on_conflict
        return self

    # --- run it ---
    def execute(self):
        rows = self.db.rows(self.table)
        if self.action == "select":
            out = [r for r in rows if all(f(r) for f in self.filters)]
            if self.order_by:
                col, desc = self.order_by
                out.sort(key=lambda r: r.get(col) or "", reverse=desc)
            if self.limit_n is not None:
                out = out[: self.limit_n]
            return SimpleNamespace(data=copy.deepcopy(out))
        if self.action == "update":
            out = []
            for r in rows:
                if all(f(r) for f in self.filters):
                    r.update(copy.deepcopy(self.payload))
                    out.append(copy.deepcopy(r))
            return SimpleNamespace(data=out)
        payload = self.payload if isinstance(self.payload, list) else [self.payload]
        out = []
        for new in payload:
            new = copy.deepcopy(new)
            existing = None
            if self.action == "upsert" and self.on_conflict and new.get(self.on_conflict) is not None:
                existing = next((r for r in rows if r.get(self.on_conflict) == new[self.on_conflict]), None)
            if existing:  # like Postgres "on conflict do update": only the sent columns change
                existing.update(new)
                out.append(copy.deepcopy(existing))
                continue
            for col in UNIQUE.get(self.table, []):
                if new.get(col) is not None and any(r.get(col) == new[col] for r in rows):
                    raise Exception(f"duplicate key value violates unique constraint ({self.table}.{col})")
            row = {**DEFAULTS.get(self.table, {}), "id": str(uuid.uuid4()),
                   "created_at": f"{datetime.now(timezone.utc).isoformat()}#{next(_clock):06d}", **new}
            rows.append(row)
            out.append(copy.deepcopy(row))
        return SimpleNamespace(data=out)


# ---------- Google Places ----------

def place_json(i, **overrides):
    """A realistic Places API result. Override any field, or set it to None to remove it."""
    p = {
        "id": f"place-{i}",
        "displayName": {"text": f"Business {i}", "languageCode": "en"},
        "formattedAddress": f"{i} Main St, Austin, TX",
        "nationalPhoneNumber": f"(512) 555-{i:04d}",
        "rating": 4.5,
        "userRatingCount": 50,
        "regularOpeningHours": {"weekdayDescriptions": ["Monday: 8AM-5PM"]},
        "primaryType": "plumber",
        "googleMapsUri": f"https://maps.google.com/?cid={i}",
        "photos": [{"name": f"places/place-{i}/photos/a", "widthPx": 800, "heightPx": 600}],
    }
    p.update(overrides)
    return {k: v for k, v in p.items() if v is not None}


class FakePlacesAPI:
    """Pretends to be Google. Give it a dict of query -> list of places; it pages 20 at a time.

    `fail_first` = a list of status codes to return before succeeding (to test retries).
    Use .transport with httpx.Client(transport=...).
    """

    def __init__(self, results: dict[str, list[dict]], fail_first=()):
        import httpx
        self.results, self.fail_first = results, list(fail_first)
        self.calls: list[dict] = []
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request):
        import json
        import httpx
        body = json.loads(request.content)
        self.calls.append({"body": body, "headers": dict(request.headers)})
        if self.fail_first:
            return httpx.Response(self.fail_first.pop(0), headers={"Retry-After": "3"}, json={"error": "busy"})
        everything = self.results.get(body["textQuery"], [])
        start = int(body.get("pageToken", "0"))
        page = everything[start:start + body["pageSize"]]
        data = {"places": page}
        if start + body["pageSize"] < len(everything):
            data["nextPageToken"] = str(start + body["pageSize"])
        return httpx.Response(200, json=data)


# ---------- Claude ----------

def good_enrichment(**overrides):
    from leads.models import Enrichment
    data = dict(summary="A family plumbing business in Austin.", services=["Leak repair", "Water heaters"],
                site_sections=["Services", "About", "Reviews", "Contact"],
                selling_points=["50 reviews but no website", "Missed calls cost jobs", "Only on Facebook"],
                tone="family-run")
    data.update(overrides)
    return Enrichment(**data)


class FakeClaude:
    """Pretends to be anthropic.Anthropic(). Each queued item is returned by one
    beta.messages.parse call: an Enrichment, an Exception to raise, or a
    (stop_reason, parsed_output) tuple."""

    def __init__(self, *responses):
        from types import SimpleNamespace
        self.queue = list(responses)
        self.calls: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def _parse(self, **kwargs):
        from types import SimpleNamespace
        self.calls.append(kwargs)
        item = self.queue.pop(0) if self.queue else good_enrichment()
        if isinstance(item, Exception):
            raise item
        if isinstance(item, tuple):
            return SimpleNamespace(stop_reason=item[0], parsed_output=item[1])
        return SimpleNamespace(stop_reason="end_turn", parsed_output=item)
