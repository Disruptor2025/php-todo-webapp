from leads.dnc import DncList, normalize_phone


def test_phone_formats_match():
    assert normalize_phone("(512) 555-0100") == normalize_phone("+1 512 555 0100") == "5125550100"
    assert normalize_phone("") is None and normalize_phone(None) is None


def test_blocks_by_place_id_phone_or_email():
    dnc = DncList([{"place_id": "p1"}, {"phone": "512-555-0199"}, {"email": "No@Thanks.com"}])
    assert dnc.blocks(place_id="p1")
    assert dnc.blocks(phone="+1 (512) 555-0199")
    assert dnc.blocks(email="no@thanks.com ")
    assert not dnc.blocks(place_id="p2", phone="512-555-0000", email="yes@please.com")
    assert not dnc.blocks()


def test_loads_from_db(db):
    db.table("dnc").insert([{"place_id": "p9", "reason": "asked us to stop"}]).execute()
    assert DncList.load(db).blocks(place_id="p9")
