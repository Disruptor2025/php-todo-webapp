"""Approvals: every action that spends money must be approved by a human first.

How it works:
1. Code calls `request(...)` describing what it wants to do and roughly what it costs.
   This adds a row to the `approvals` table with status "pending" (or finds the
   existing one for the exact same request).
2. You approve or reject it in the dashboard (status -> "approved"/"rejected").
3. The code calls `consume(...)` right before spending. It checks the row is
   approved AND matches the exact same request, then marks it "used".
   One approval = one run. Running again needs a new approval.

"Same request" is checked with a fingerprint (hash) of the request details, so
an approval for "100 plumbers in Austin" can't be reused for "500 in Dallas".
"""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

PENDING, APPROVED, REJECTED, USED = "pending", "approved", "rejected", "used"


class ApprovalError(Exception):
    """Raised when we try to spend money without a valid approval."""


@dataclass
class Approval:
    id: str
    status: str
    description: str
    estimated_cost_usd: float


def fingerprint(kind: str, payload: dict) -> str:
    """A stable hash of the request. sort_keys makes key order irrelevant."""
    text = json.dumps({"kind": kind, "payload": payload}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Approvals:
    def __init__(self, db):
        self.db = db

    def _latest(self, kind: str, payload: dict) -> dict | None:
        """Most recent pending/approved row for this exact request, if any."""
        rows = (
            self.db.table("approvals")
            .select("*")
            .eq("kind", kind)
            .eq("payload_hash", fingerprint(kind, payload))
            .in_("status", [PENDING, APPROVED])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def request(self, kind: str, description: str, estimated_cost_usd: float, payload: dict) -> Approval:
        """Find the open approval for this request, or create a new pending one."""
        row = self._latest(kind, payload)
        if row is None:
            row = (
                self.db.table("approvals")
                .insert({
                    "kind": kind,
                    "description": description,
                    "estimated_cost_usd": round(estimated_cost_usd, 2),
                    "payload": payload,
                    "payload_hash": fingerprint(kind, payload),
                    "status": PENDING,
                })
                .execute()
                .data[0]
            )
        return Approval(row["id"], row["status"], row["description"], float(row["estimated_cost_usd"]))

    def status(self, approval_id: str) -> str:
        rows = self.db.table("approvals").select("status").eq("id", approval_id).execute().data
        if not rows:
            raise ApprovalError(f"Approval {approval_id} not found")
        return rows[0]["status"]

    def consume(self, approval_id: str, kind: str, payload: dict) -> None:
        """Check the approval is valid for this exact request, then mark it used.

        Call this immediately BEFORE spending money. Marking it used first means a
        crash halfway can't lead to the same approval being spent twice.
        """
        rows = self.db.table("approvals").select("*").eq("id", approval_id).execute().data
        if not rows:
            raise ApprovalError(f"Approval {approval_id} not found")
        row = rows[0]
        if row["status"] != APPROVED:
            raise ApprovalError(f"Approval {approval_id} is '{row['status']}', not approved")
        if row["kind"] != kind or row["payload_hash"] != fingerprint(kind, payload):
            raise ApprovalError(f"Approval {approval_id} was given for a different request")
        self.db.table("approvals").update({"status": USED, "used_at": _now()}).eq("id", approval_id).execute()
