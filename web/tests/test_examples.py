"""Tests for the Examples gallery and demo sites."""
from conftest import load_data


def test_gallery_links_to_every_example(page):
    soup = page("/examples")
    for ex in load_data("examples.json"):
        card = soup.select_one(f'[data-example="{ex["slug"]}"]')
        assert card["href"] == f"/examples/{ex['slug']}"


def test_gallery_says_businesses_are_fictional(page):
    text = page("/examples").get_text().lower()
    assert "made up" in text


def test_each_demo_site_is_built_and_labelled_fictional(page):
    for ex in load_data("examples.json"):
        soup = page(f"/examples/{ex['slug']}")
        assert soup.find("h1").get_text(strip=True) == ex["name"]
        banner = soup.select_one("[data-demo-banner]")
        assert banner is not None and "fictional" in banner.get_text().lower()
        assert "(demo site)" in soup.title.string


def test_examples_have_required_fields():
    for ex in load_data("examples.json"):
        for key in ["slug", "name", "type", "town", "color", "tagline", "about", "services", "hours"]:
            assert ex.get(key), f"{ex.get('slug')}: missing {key}"
