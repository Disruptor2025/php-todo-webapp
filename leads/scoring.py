"""Score a lead from 0 to 100. Simple and explainable on purpose.

    Reviews          up to 35   more reviews = established, busy, can afford us
    Rating           up to 25   happy customers = good business to work with
    Opening hours    up to 15   hours listed = active business
    Category value   up to 25   home services/medical are worth more than food
    ------------------------
    Total            up to 100

A phone number is REQUIRED: without one we can't sell to them, so the score is 0.
"""
import math
import re

from leads.models import Place

MAX_REVIEWS, MAX_RATING, MAX_HOURS, MAX_CATEGORY = 35, 25, 15, 25
REVIEWS_FOR_FULL_POINTS = 200

# Category groups, checked in order; first match wins.
# A keyword ending in "*" matches the start of a word ("plumb*" -> "plumbing");
# otherwise the whole word must match (so "spa" doesn't match "spanish").
CATEGORY_GROUPS = [
    ("home services", 25, ["plumb*", "electric*", "hvac", "heating", "roof*", "locksmith*", "clean*", "maid*",
                           "pest", "landscap*", "lawn", "paint*", "contractor*", "handyman", "moving", "movers",
                           "garage", "carpet*", "pool", "window*", "floor*", "gutter*", "tree", "fenc*", "remodel*"]),
    ("medical", 25, ["dent*", "doctor*", "clinic*", "physio*", "chiropract*", "medical", "health*", "optometr*",
                     "veterinar*", "vet", "therap*", "orthodont*", "pharmac*", "podiatr*"]),
    ("auto", 20, ["car", "auto*", "mechanic*", "tire*", "tyre*", "body", "detailing", "transmission"]),
    ("beauty", 18, ["salon*", "nail*", "hair*", "barber*", "beauty", "spa", "massage*", "lash*", "brow*",
                    "tattoo*", "esthetic*"]),
    ("professional", 15, ["lawyer*", "attorney*", "accountant*", "accounting", "insurance", "real", "tutor*",
                          "photograph*"]),
    ("food", 10, ["restaurant*", "cafe*", "coffee", "bakery", "bakeries", "food", "bar", "pizza*", "diner",
                  "takeaway", "catering", "grill", "taqueria*", "bistro"]),
]
OTHER_CATEGORY = ("other", 12)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def category_group(*texts: str | None) -> tuple[str, int]:
    """Find the category group for Google's primaryType first, then our search term."""
    for text in texts:
        if not text:
            continue
        words = _words(text)
        for name, points, keywords in CATEGORY_GROUPS:
            for kw in keywords:
                if kw.endswith("*"):
                    if any(w.startswith(kw[:-1]) for w in words):
                        return name, points
                elif kw in words:
                    return name, points
    return OTHER_CATEGORY


def score_place(place: Place, search_category: str | None = None) -> tuple[int, str, dict]:
    """Returns (score, one-line reason, breakdown dict)."""
    if not place.phone:
        breakdown = {"phone": {"points": 0, "why": "No phone number: can't contact, score set to 0"}}
        return 0, "No phone number listed (required)", breakdown

    # Reviews: log scale, so going from 0->20 reviews matters more than 180->200.
    n = place.user_rating_count
    reviews = round(MAX_REVIEWS * min(1.0, math.log10(1 + n) / math.log10(1 + REVIEWS_FOR_FULL_POINTS)))

    # Rating: 3.0 stars or below = 0 points, 5.0 = full points, straight line in between.
    if place.rating is None or n == 0:
        rating, rating_why = 0, "No rating"
    else:
        rating = round(MAX_RATING * min(1.0, max(0.0, (place.rating - 3.0) / 2.0)))
        rating_why = f"{place.rating} stars"

    hours = MAX_HOURS if place.opening_hours else 0
    group, category = category_group(place.primary_type, search_category)

    breakdown = {
        "reviews": {"points": reviews, "max": MAX_REVIEWS, "why": f"{n} reviews"},
        "rating": {"points": rating, "max": MAX_RATING, "why": rating_why},
        "hours": {"points": hours, "max": MAX_HOURS, "why": "Opening hours listed" if hours else "No opening hours"},
        "category": {"points": category, "max": MAX_CATEGORY, "why": group},
    }
    total = reviews + rating + hours + category
    reason = " · ".join(
        f"{k.capitalize()}: {v['why']} → {v['points']}/{v['max']}" for k, v in breakdown.items()
    )
    return total, reason, breakdown
