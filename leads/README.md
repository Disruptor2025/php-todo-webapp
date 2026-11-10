# Leads (`/leads`)

Finds local businesses with no real website, scores them, enriches the best ones with Claude, and saves them to Supabase.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env          # fill in Supabase, Google Places and Anthropic keys
```
Run `supabase/migrations/*.sql` in the Supabase SQL editor (in order).
In Google Cloud, enable **Places API (New)** for your key.

## Find leads

```bash
python -m leads.find --city "Austin, TX" --categories plumber,salon --limit 100
```

1. The first run **spends nothing**. It creates an `approvals` row with the worst-case cost and prints its id.
2. Approve it in the dashboard (until that exists: `update approvals set status='approved' where id='...'`).
3. Run the same command again (or add `--wait` to keep checking). It runs once and marks the approval `used`.

Options: `--enrich-top 20` (how many to enrich with Claude, 0 = none), `--top 20` (rows to print).
The limit is split across categories, max 60 per category (Google's limit).

## Scoring (0-100)

| Factor | Points | Rule |
|---|---|---|
| Reviews | 35 | log scale, 200+ reviews = full points |
| Rating | 25 | 3.0★ or below = 0, 5.0★ = 25 |
| Opening hours listed | 15 | all or nothing |
| Category | 25 | home services/medical 25, auto 20, beauty 18, professional 15, other 12, food 10 |

No phone number = not saved (we can't contact them). Each lead stores `score_reason` (one line) and
`score_breakdown` (points per factor). Change the numbers in `leads/scoring.py`.

## Which businesses count as leads

- No `websiteUri` → `website_status = 'none'`
- Website is Facebook, Yelp, Linktree or Instagram → `'social_only'`
- Anything else is a real website and is skipped.

## Do-not-contact

Add rows to `dnc` with a `place_id`, `phone` and/or `email`. Matching businesses are never saved,
both from searches and from the website form (the form still replies "ok" so the list isn't revealed).

## Reruns

`place_id` is unique, so reruns update existing leads. `status`, `created_at` and an existing
`enrichment` are never overwritten, and already-enriched leads aren't sent to Claude again.

## API (for the website)

```bash
uvicorn leads.api:app --reload    # http://localhost:8000
```
- `POST /leads/inbound`: free preview form (JSON or plain form post). Creates a lead with `source='inbound'`.
- `POST /leads/waitlist`: founders waitlist.

Set `CORS_ORIGINS` to the website's address.

## Tests

`python -m pytest` uses fake Google Places, Claude and Supabase. Nothing real is called.
