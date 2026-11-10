import pytest

from shared.approvals import ApprovalError, Approvals

PAYLOAD = {"city": "Austin, TX", "categories": ["plumber"], "limit": 20}


def approve(db, approval_id):
    """Simulates you clicking Approve in the dashboard."""
    db.table("approvals").update({"status": "approved"}).eq("id", approval_id).execute()


def test_request_creates_pending_row(db):
    a = Approvals(db).request("leads.find", "Find plumbers", 1.234, PAYLOAD)
    assert a.status == "pending"
    assert a.estimated_cost_usd == 1.23
    assert len(db.rows("approvals")) == 1


def test_same_request_reuses_open_approval(db):
    approvals = Approvals(db)
    first = approvals.request("leads.find", "x", 1, PAYLOAD)
    second = approvals.request("leads.find", "x", 1, dict(reversed(PAYLOAD.items())))  # key order doesn't matter
    assert first.id == second.id
    assert len(db.rows("approvals")) == 1


def test_different_request_needs_new_approval(db):
    approvals = Approvals(db)
    a = approvals.request("leads.find", "x", 1, PAYLOAD)
    b = approvals.request("leads.find", "x", 1, {**PAYLOAD, "limit": 500})
    assert a.id != b.id


def test_consume_requires_approved_status(db):
    approvals = Approvals(db)
    a = approvals.request("leads.find", "x", 1, PAYLOAD)
    with pytest.raises(ApprovalError, match="pending"):
        approvals.consume(a.id, "leads.find", PAYLOAD)


def test_consume_rejects_mismatched_request(db):
    approvals = Approvals(db)
    a = approvals.request("leads.find", "x", 1, PAYLOAD)
    approve(db, a.id)
    with pytest.raises(ApprovalError, match="different request"):
        approvals.consume(a.id, "leads.find", {**PAYLOAD, "limit": 999})


def test_approval_can_only_be_used_once(db):
    approvals = Approvals(db)
    a = approvals.request("leads.find", "x", 1, PAYLOAD)
    approve(db, a.id)
    approvals.consume(a.id, "leads.find", PAYLOAD)
    assert approvals.status(a.id) == "used"
    with pytest.raises(ApprovalError):
        approvals.consume(a.id, "leads.find", PAYLOAD)
    # Asking again after it's used creates a fresh pending approval.
    assert approvals.request("leads.find", "x", 1, PAYLOAD).id != a.id


def test_rejected_approval_cannot_be_used(db):
    approvals = Approvals(db)
    a = approvals.request("leads.find", "x", 1, PAYLOAD)
    db.table("approvals").update({"status": "rejected"}).eq("id", a.id).execute()
    with pytest.raises(ApprovalError, match="rejected"):
        approvals.consume(a.id, "leads.find", PAYLOAD)
