"""Command line: find leads and print the best ones.

    python -m leads.find --city "Austin, TX" --categories plumber,salon --limit 100

The first run creates an approval request (it costs money) and stops.
Approve it in the dashboard, then run the same command again
(or add --wait to keep checking until you approve it).
"""
import argparse
import logging
import sys
import time

from leads.dnc import DncList
from leads.pipeline import KIND, FindRequest, RunReport, run
from leads.places import PlacesClient
from leads.store import LeadStore
from shared.approvals import APPROVED, PENDING, Approvals
from shared.config import get_settings

EXIT_WAITING = 2


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="python -m leads.find", description="Find local businesses with no website.")
    ap.add_argument("--city", required=True, help='e.g. "Austin, TX"')
    ap.add_argument("--categories", required=True, help="comma-separated, e.g. plumber,nail salon,auto repair")
    ap.add_argument("--limit", type=int, default=100, help="max businesses to fetch in total (default 100)")
    ap.add_argument("--enrich-top", type=int, default=20, help="enrich this many top leads with Claude (default 20)")
    ap.add_argument("--top", type=int, default=20, help="how many leads to print (default 20)")
    ap.add_argument("--wait", action="store_true", help="keep checking until the approval is decided")
    return ap.parse_args(argv)


def format_table(leads: list[dict], top: int) -> str:
    header = f"{'#':>2}  {'Score':>5}  {'Business':<30}  {'Category':<14}  {'Rating':<11}  {'Phone':<16}  {'Website':<11}  AI"
    lines = [header, "-" * len(header)]
    for i, l in enumerate(leads[:top], 1):
        rating = f"{l['rating'] or '-'} ({l['reviews']})"
        lines.append(
            f"{i:>2}  {l['score']:>5}  {l['name'][:30]:<30}  {l['category'][:14]:<14}  {rating:<11}  "
            f"{(l['phone'] or '')[:16]:<16}  {l['website_status']:<11}  {'yes' if l['enriched'] else ''}"
        )
    return "\n".join(lines)


def format_summary(r: RunReport) -> str:
    return (f"Fetched {r.fetched} ({r.unique} unique) using {r.places_requests} Places requests. "
            f"Skipped: {r.skipped_has_website} have a website, {r.skipped_no_phone} no phone, "
            f"{r.skipped_dnc} do-not-contact.\n"
            f"Saved {r.saved_new} new, updated {r.updated_existing}. "
            f"Enriched {r.enriched} with Claude ({r.claude_calls} calls).")


def wait_for_decision(approvals: Approvals, approval_id: str, sleep, poll_seconds=15, timeout_seconds=1800) -> str:
    waited = 0
    while waited < timeout_seconds:
        status = approvals.status(approval_id)
        if status != PENDING:
            return status
        sleep(poll_seconds)
        waited += poll_seconds
    return PENDING


def main(argv=None, *, db=None, places=None, claude=None, sleep=time.sleep) -> int:
    """`db`, `places` and `claude` can be passed in by tests; normally they're created from .env."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    settings = get_settings()
    try:
        req = FindRequest(args.city, args.categories.split(","), args.limit, args.enrich_top)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if db is None:
        from shared.db import get_db
        db = get_db()
    approvals = Approvals(db)
    cost = req.estimated_cost(settings.PLACES_COST_PER_REQUEST_USD, settings.ENRICH_COST_PER_LEAD_USD)
    approval = approvals.request(KIND, req.describe(), cost, req.payload())

    status = approval.status
    if status == PENDING:
        print(f"Needs approval (estimated max ${approval.estimated_cost_usd:.2f}): {approval.description}")
        print(f"Approval id: {approval.id}. Approve it in the dashboard, then run this command again.")
        if not args.wait:
            return EXIT_WAITING
        print("Waiting for a decision...")
        status = wait_for_decision(approvals, approval.id, sleep)
    if status != APPROVED:
        print(f"Not running: approval is '{status}'.")
        return EXIT_WAITING if status == PENDING else 1

    # Approved: create the paid clients only now.
    places = places or PlacesClient(settings.require("GOOGLE_PLACES_API_KEY"))
    enricher = None
    if req.enrich_top > 0:
        from leads.enrich import Enricher
        if claude is None:
            import anthropic
            claude = anthropic.Anthropic(api_key=settings.require("ANTHROPIC_API_KEY"))
        enricher = Enricher(claude, settings.CLAUDE_MODEL)

    report = run(req, approval_id=approval.id, approvals=approvals, places=places, enricher=enricher,
                 store=LeadStore(db), dnc=DncList.load(db))
    print(format_summary(report))
    print()
    print(format_table(report.leads, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
