def filter_by_rating(restaurants, conditions=None):
    """요청에서 추출한 별점 비교 조건을 응답의 rating 값에 적용합니다.
    rating이 None이거나 누락된 경우 0으로 처리해 제외합니다.
    """
    conditions = conditions or []
    print(f"[Tool: rating_filter] conditions={conditions}")

    if not conditions:
        return restaurants

    filtered = [
        restaurant for restaurant in restaurants
        if rating_matches(restaurant.get("rating"), conditions)
    ]

    print(f"[Tool: rating_filter] {len(restaurants)}개 -> {len(filtered)}개")
    return filtered


def filter_by_price(restaurants, max_price=2):
    """가격대 기준으로 맛집 목록을 필터링합니다.
    price_level이 None(Google Places 미제공)인 경우 조건 통과시킵니다.
    price_level=0은 '무료/미분류'가 아닌 '정보 없음'으로 처리합니다.
    """
    max_price = _safe_int(max_price, default=2)
    print(f"[Tool: rating_filter] max_price={max_price}")

    filtered = [
        restaurant for restaurant in restaurants
        if _price_passes(restaurant.get("price_level"), max_price)
    ]

    print(f"[Tool: rating_filter] {len(restaurants)}개 -> {len(filtered)}개")
    return filtered


def filter_by_review_count(restaurants, min_reviews=50):
    """리뷰 수 기준으로 맛집 목록을 필터링합니다.
    review_count가 None이거나 누락된 경우 0으로 처리합니다.
    """
    min_reviews = _safe_int(min_reviews, default=50)
    print(f"[Tool: rating_filter] min_reviews={min_reviews}")

    filtered = [
        restaurant for restaurant in restaurants
        if _safe_int(restaurant.get("review_count")) >= min_reviews
    ]

    if not filtered:
        print(f"[Tool: rating_filter] ⚠️ 리뷰 {min_reviews}개 이상 결과 없음. 필터를 건너뜁니다.")
        return restaurants

    print(f"[Tool: rating_filter] {len(restaurants)}개 -> {len(filtered)}개")
    return filtered


# ── 내부 유틸 ────────────────────────────────────────────────────

def _safe_float(value, default=0.0) -> float:
    """None이거나 변환 불가인 경우 default를 반환합니다."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0) -> int:
    """None이거나 변환 불가인 경우 default를 반환합니다."""
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def rating_matches(rating, conditions) -> bool:
    if rating is None:
        return False
    value = _safe_float(rating)
    comparisons = {
        "gte": lambda expected: value >= expected,
        "lte": lambda expected: value <= expected,
        "gt": lambda expected: value > expected,
        "lt": lambda expected: value < expected,
    }
    return all(
        condition.get("operator") in comparisons
        and comparisons[condition["operator"]](_safe_float(condition.get("value")))
        for condition in conditions
    )


def _price_passes(price_level, max_price: int) -> bool:
    """
    가격 조건 통과 여부를 판단합니다.
    - None 또는 0: Google Places 미제공 → 조건 충족 여부를 알 수 없어 제외
    - 1~4: 실제 가격 레벨 → max_price와 비교
    """
    if price_level is None or price_level == 0:
        return False
    return int(price_level) <= max_price


def sort_by_review_count(restaurants):
    """리뷰 수 기준 내림차순 정렬합니다."""
    print("[Tool: rating_filter] 리뷰 수 기준 정렬")
    return sorted(restaurants, key=lambda r: r.get("review_count", 0), reverse=True)
