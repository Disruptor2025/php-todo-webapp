from leads.models import Place
from leads.scoring import category_group, score_place


def place(**kw):
    base = dict(id="p", name="Biz", phone="512-555-0100", rating=4.5, user_rating_count=50,
                opening_hours={"weekdayDescriptions": []}, primary_type="plumber")
    base.update(kw)
    return Place(**base)


def test_phone_is_required():
    score, reason, breakdown = score_place(place(phone=None))
    assert score == 0 and "phone" in reason.lower()


def test_perfect_lead_scores_100():
    score, _, _ = score_place(place(rating=5.0, user_rating_count=500))
    assert score == 100


def test_score_always_between_0_and_100():
    for count in [0, 1, 10, 1000, 10**6]:
        for rating in [None, 1.0, 3.0, 4.2, 5.0]:
            for hours in [None, {"x": 1}]:
                s, _, _ = score_place(place(user_rating_count=count, rating=rating, opening_hours=hours,
                                            primary_type="restaurant"))
                assert 0 <= s <= 100


def test_more_reviews_scores_higher():
    low, _, _ = score_place(place(user_rating_count=5))
    high, _, _ = score_place(place(user_rating_count=150))
    assert high > low


def test_higher_rating_scores_higher():
    low, _, _ = score_place(place(rating=3.5))
    high, _, _ = score_place(place(rating=4.9))
    assert high > low


def test_opening_hours_add_points():
    without, _, _ = score_place(place(opening_hours=None))
    with_hours, _, _ = score_place(place())
    assert with_hours - without == 15


def test_category_value_order():
    plumber, _, _ = score_place(place(primary_type="plumber"))
    dentist, _, _ = score_place(place(primary_type="dentist"))
    salon, _, _ = score_place(place(primary_type="nail_salon"))
    restaurant, _, _ = score_place(place(primary_type="restaurant"))
    assert plumber == dentist > salon > restaurant


def test_breakdown_adds_up_and_reason_explains():
    score, reason, breakdown = score_place(place())
    assert sum(v["points"] for v in breakdown.values()) == score
    for word in ["Reviews", "Rating", "Hours", "Category"]:
        assert word in reason


def test_rating_ignored_without_reviews():
    _, _, breakdown = score_place(place(rating=5.0, user_rating_count=0))
    assert breakdown["rating"]["points"] == 0


def test_category_matching():
    assert category_group("plumber")[0] == "home services"
    assert category_group("house_cleaning_service")[0] == "home services"
    assert category_group("dental_clinic")[0] == "medical"
    assert category_group("car_repair")[0] == "auto"
    assert category_group(None, "auto repair")[0] == "auto"
    assert category_group("barber_shop")[0] == "beauty"       # not "bar"
    assert category_group("spanish_restaurant")[0] == "food"  # not "spa"
    assert category_group("museum")[0] == "other"
