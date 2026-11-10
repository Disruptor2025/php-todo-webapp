"""Do-not-contact list. Checked before any lead is saved.

A business matches if ANY of these match a row in the `dnc` table:
place_id, phone number, or email.
"""
import re


def normalize_phone(phone: str | None) -> str | None:
    """Keep digits only and compare the last 10, so '(512) 555-0100' == '+1 512 555 0100'."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return digits[-10:] if len(digits) >= 7 else None


def normalize_email(email: str | None) -> str | None:
    return email.strip().lower() if email and email.strip() else None


class DncList:
    def __init__(self, rows: list[dict]):
        self.place_ids = {r["place_id"] for r in rows if r.get("place_id")}
        self.phones = {p for r in rows if (p := normalize_phone(r.get("phone")))}
        self.emails = {e for r in rows if (e := normalize_email(r.get("email")))}

    @classmethod
    def load(cls, db) -> "DncList":
        # The list is small, so load it all once per run instead of one query per lead.
        return cls(db.table("dnc").select("place_id, phone, email").execute().data)

    def blocks(self, place_id: str | None = None, phone: str | None = None, email: str | None = None) -> bool:
        return (
            (place_id is not None and place_id in self.place_ids)
            or (normalize_phone(phone) in self.phones if normalize_phone(phone) else False)
            or (normalize_email(email) in self.emails if normalize_email(email) else False)
        )
