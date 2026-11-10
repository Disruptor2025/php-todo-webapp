"""Tests for the Home page."""
import json

from conftest import load_data


def test_headline_mentions_getting_found_and_calls(page):
    h1 = page("/").find("h1").get_text()
    assert "found" in h1.lower()
    assert "call" in h1.lower()


def test_three_tiers_with_prices_from_json(page):
    soup = page("/")
    pricing = load_data("pricing.json")
    cards = soup.select("[data-tier]")
    assert [c["data-tier"] for c in cards] == ["site", "voice", "grow"]
    for card, tier in zip(cards, pricing["tiers"]):
        assert tier["name"] in card.get_text()
        price = card.select_one("[data-price]").get_text()
        assert price == f"{pricing['currency']}{tier['monthly']:,}"


def test_how_it_works_has_three_steps(page):
    steps = page("/").select("#how ol > li")
    assert len(steps) == 3


def test_live_demo_has_chat_and_call_buttons(page):
    soup = page("/")
    site = load_data("site.json")
    chat = soup.select_one("#demo-chat")
    assert chat["data-business-id"] == site["demo"]["businessId"]
    # The demo phone comes from PUBLIC_DEMO_PHONE (set in conftest.TEST_ENV)
    assert soup.select_one("#demo-call")["href"] == "tel:+15550100199"
    # The demo business must be clearly labelled as made-up.
    assert "made-up" in soup.select_one("#demo").get_text()


def test_faq_lists_every_question_and_has_schema(page):
    soup = page("/")
    faq = load_data("faq.json")
    questions = [s.get_text(strip=True) for s in soup.select("#faq summary")]
    for item in faq:
        assert any(item["q"] in q for q in questions)
    schemas = [json.loads(s.string) for s in soup.select('script[type="application/ld+json"]')]
    assert any(s["@type"] == "FAQPage" for s in schemas)


def test_cta_free_preview_links_to_form(page):
    soup = page("/")
    ctas = [a for a in soup.find_all("a") if "free website preview" in a.get_text().lower()]
    assert ctas and all(a["href"] == "/preview" for a in ctas)


def test_results_section_hidden_while_empty(page):
    assert load_data("results.json") == [], "results.json has entries: update this test"
    assert page("/").select_one("#results") is None


def test_no_testimonials_or_client_logos(page):
    soup = page("/")
    text = soup.get_text().lower()
    assert "testimonial" not in text
    assert "trusted by" not in text
    assert soup.find("blockquote") is None
