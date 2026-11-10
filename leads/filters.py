"""Decide if a business is a lead: no website, or only a social/listing page."""
from urllib.parse import urlparse

# If their "website" is really one of these, they still need a proper site.
SOCIAL_DOMAINS = {
    "facebook.com", "fb.com", "fb.me", "m.facebook.com",
    "yelp.com",
    "linktr.ee", "linktree.com",
    "instagram.com",
}


def _domain(url: str) -> str:
    # urlparse needs a scheme to find the domain, e.g. "facebook.com/x" -> add "https://"
    if "://" not in url:
        url = "https://" + url
    host = (urlparse(url).hostname or "").lower()
    return host.removeprefix("www.")


def is_social(url: str) -> bool:
    host = _domain(url)
    # Matches "facebook.com" and subdomains like "business.facebook.com".
    # Yelp has country sites (yelp.co.uk, yelp.ca), so match any "yelp." domain too.
    return host.startswith("yelp.") or any(host == d or host.endswith("." + d) for d in SOCIAL_DOMAINS)


def website_status(website_uri: str | None) -> str | None:
    """'none' = no website, 'social_only' = only Facebook/Yelp/etc, None = has a real site (not a lead)."""
    if not website_uri or not website_uri.strip():
        return "none"
    if is_social(website_uri):
        return "social_only"
    return None
