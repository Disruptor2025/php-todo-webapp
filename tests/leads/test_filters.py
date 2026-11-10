import pytest

from leads.filters import website_status


@pytest.mark.parametrize("url", [None, "", "   "])
def test_missing_website_is_a_lead(url):
    assert website_status(url) == "none"


@pytest.mark.parametrize("url", [
    "https://www.facebook.com/joesplumbing",
    "http://facebook.com/pages/joe",
    "https://m.facebook.com/joe",
    "https://business.facebook.com/joe",
    "facebook.com/joe",
    "https://www.yelp.com/biz/joes-plumbing-austin",
    "https://www.yelp.co.uk/biz/joes",
    "https://linktr.ee/joesplumbing",
    "https://www.instagram.com/joesplumbing",
    "https://fb.me/joes",
])
def test_social_pages_are_flagged(url):
    assert website_status(url) == "social_only"


@pytest.mark.parametrize("url", [
    "https://joesplumbing.com",
    "https://www.notfacebook.com",       # contains "facebook" but is a different site
    "https://facebook.com.scam.example",  # tricky: not really facebook
    "https://yelpme.com",
])
def test_real_websites_are_not_leads(url):
    assert website_status(url) is None
