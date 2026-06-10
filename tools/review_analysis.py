from tools.restaurant_search import enrich_place_reviews


ATMOSPHERE_KEYWORDS = [
    "분위기",
    "인테리어",
    "데이트",
    "친구랑 오기 좋음",
    "조용함",
    "감성",
    "bar",
    "cafe",
    "bakery",
    "night_club",
]


def filter_by_atmosphere(restaurants):
    """리뷰 키워드 기반으로 분위기 좋은 식당만 남깁니다."""
    print("[Tool: review_analysis] 분위기 키워드 분석 시작")
    print(f"[Tool: review_analysis] keywords={ATMOSPHERE_KEYWORDS}")

    enrich_place_reviews(restaurants)
    filtered = []

    for restaurant in restaurants:
        is_good = has_good_atmosphere(restaurant)
        restaurant["is_good_atmosphere"] = is_good

        if is_good:
            filtered.append(restaurant)

    print(f"[Tool: review_analysis] {len(restaurants)}개 -> {len(filtered)}개")
    return filtered


def has_good_atmosphere(restaurant):
    reviews = restaurant.get("reviews", [])
    joined_reviews = " ".join([
        *reviews,
        restaurant.get("name", ""),
        restaurant.get("address", ""),
        " ".join(restaurant.get("place_types", [])),
    ]).lower()

    return any(keyword.lower() in joined_reviews for keyword in ATMOSPHERE_KEYWORDS)
