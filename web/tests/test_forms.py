"""Tests for the free preview form and the hidden founders waitlist."""
from conftest import TEST_ENV, load_data

API = TEST_ENV["PUBLIC_API_URL"]


def test_preview_form_posts_to_leads_inbound(page):
    form = page("/preview").select_one("#preview-form")
    assert form["action"] == f"{API}/leads/inbound"
    assert form["method"] == "post"


def test_preview_form_has_required_fields(page):
    form = page("/preview").select_one("#preview-form")
    required = {i["name"] for i in form.select("input[required]")}
    assert required == {"business_name", "city", "phone", "email"}
    assert form.select_one('input[name="google_maps_url"]')["type"] == "url"
    assert form.select_one('input[name="email"]')["type"] == "email"
    assert form.select_one('input[name="phone"]')["type"] == "tel"


def test_every_input_has_a_label(page):
    for url in ["/preview", "/founders"]:
        soup = page(url)
        labels = {l["for"] for l in soup.select("label[for]")}
        for inp in soup.select("form input"):
            assert inp["id"] in labels, f"{url}: input {inp['name']} has no label"


def test_preview_form_has_spam_trap(page):
    trap = page("/preview").select_one('#preview-form input[name="website"]')
    assert trap is not None and trap["tabindex"] == "-1"


def test_founders_waitlist_posts_to_backend(page):
    form = page("/founders").select_one("#waitlist-form")
    assert form["action"] == f"{API}/leads/waitlist"


def test_founders_page_is_hidden(page, built_site):
    # Not in the main menu...
    assert all(item["href"] != "/founders" for item in load_data("site.json")["nav"])
    for url in ["/", "/pricing", "/examples", "/preview"]:
        assert page(url).select_one('a[href="/founders"]') is None
    # ...asks search engines not to index it...
    assert page("/founders").select_one('meta[name="robots"]')["content"].startswith("noindex")
    # ...and is left out of the sitemap.
    sitemap = (built_site / "sitemap-0.xml").read_text()
    assert "/founders" not in sitemap
