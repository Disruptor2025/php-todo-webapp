"""Tests for legal pages and SEO basics on every public page."""
import json

from conftest import TEST_ENV

SITE = TEST_ENV["PUBLIC_SITE_URL"]
PUBLIC_PAGES = ["/", "/examples", "/pricing", "/preview", "/legal/privacy", "/legal/terms", "/legal/ai-receptionist"]


def test_privacy_and_terms_are_marked_placeholder(page):
    for url in ["/legal/privacy", "/legal/terms"]:
        assert page(url).select_one("[data-placeholder]") is not None


def test_ai_receptionist_page_explains_ai_and_data(page):
    text = page("/legal/ai-receptionist").get_text().lower()
    assert "ai assistant" in text
    for topic in ["what we record", "how long we keep it", "delete"]:
        assert topic in text


def test_footer_links_to_all_legal_pages(page):
    footer = page("/").find("footer")
    hrefs = {a["href"] for a in footer.find_all("a")}
    assert {"/legal/privacy", "/legal/terms", "/legal/ai-receptionist"} <= hrefs


def test_every_page_has_unique_title_and_description(page):
    titles = set()
    for url in PUBLIC_PAGES:
        soup = page(url)
        title = soup.title.string
        assert title and title not in titles, f"duplicate/missing title on {url}"
        titles.add(title)
        desc = soup.select_one('meta[name="description"]')["content"]
        assert 50 <= len(desc) <= 170, f"{url}: description length {len(desc)}"
        assert soup.select_one('link[rel="canonical"]')["href"].startswith(SITE)
        assert len(soup.find_all("h1")) == 1, f"{url}: should have exactly one h1"


def test_organization_schema_on_every_page(page):
    for url in PUBLIC_PAGES:
        schemas = [json.loads(s.string) for s in page(url).select('script[type="application/ld+json"]')]
        org = next(s for s in schemas if s["@type"] == "Organization")
        assert org["name"] == "Prezence"
        assert org["url"] == f"{SITE}/"


def test_sitemap_lists_public_pages(built_site):
    assert (built_site / "sitemap-index.xml").exists()
    sitemap = (built_site / "sitemap-0.xml").read_text()
    for url in PUBLIC_PAGES:
        assert f"<loc>{SITE}{url}" in sitemap


def test_robots_txt_points_to_sitemap(built_site):
    robots = (built_site / "robots.txt").read_text()
    assert f"Sitemap: {SITE}/sitemap-index.xml" in robots


def test_chat_widget_on_every_page(page):
    for url in PUBLIC_PAGES + ["/founders"]:
        widget = page(url).find("prezence-chat")
        assert widget is not None, f"no chat widget on {url}"
        assert widget["business-id"] == "prezence"
        assert widget["api-url"] == TEST_ENV["PUBLIC_API_URL"]


def test_404_page_exists(built_site):
    assert (built_site / "404.html").exists()


def test_cloudflare_headers_file_copied(built_site):
    assert "/_astro/*" in (built_site / "_headers").read_text()
