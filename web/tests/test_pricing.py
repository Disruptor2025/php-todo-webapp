"""Tests for the Pricing page: every price must come from pricing.json."""
from conftest import load_data


def money(n):
    return f"{load_data('pricing.json')['currency']}{n:,}"


def test_comparison_table_has_every_tier_and_row(page):
    soup = page("/pricing")
    pricing = load_data("pricing.json")
    headers = [th.get_text(" ", strip=True) for th in soup.select("#compare thead th")]
    for tier in pricing["tiers"]:
        assert any(tier["name"] in h for h in headers)
    rows = soup.select("#compare tbody tr")
    assert len(rows) == len(pricing["comparison"])
    # Each row has one cell per tier
    assert all(len(r.find_all("td")) == len(pricing["tiers"]) for r in rows)


def test_one_time_option_prices(page):
    soup = page("/pricing")
    one = load_data("pricing.json")["oneTime"]
    prices = [p.get_text() for p in soup.select("#one-time [data-price]")]
    assert prices == [money(one["price"]), money(one["hostingMonthly"])]


def test_addons_include_payments_and_store(page):
    soup = page("/pricing")
    addons = load_data("pricing.json")["addons"]
    for addon in addons:
        card = soup.select_one(f'[data-addon="{addon["name"]}"]')
        assert card is not None
        assert card.select_one("[data-price]").get_text() == money(addon["price"])
    names = " ".join(a["name"].lower() for a in addons)
    assert "payment" in names and "store" in names


def test_every_price_on_site_exists_in_json(page):
    """Catch hardcoded prices: any [data-price] value must appear in pricing.json."""
    pricing = load_data("pricing.json")
    allowed = {money(t["monthly"]) for t in pricing["tiers"]}
    allowed |= {money(pricing["oneTime"]["price"]), money(pricing["oneTime"]["hostingMonthly"])}
    allowed |= {money(a["price"]) for a in pricing["addons"]}
    for url in ["/", "/pricing"]:
        for el in page(url).select("[data-price]"):
            assert el.get_text() in allowed, f"{url}: unexpected price {el.get_text()}"
