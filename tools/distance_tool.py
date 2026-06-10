def sort_by_distance(restaurants):
    """distance 값이 있는 경우 가까운 순서로 정렬합니다."""
    print("[Tool: distance_tool] 거리 기준 정렬 시작")

    sorted_restaurants = sorted(
        restaurants,
        key=lambda restaurant: _distance_to_number(restaurant.get("distance")),
    )

    print(f"[Tool: distance_tool] {len(sorted_restaurants)}개 정렬 완료")
    return sorted_restaurants


def _distance_to_number(distance):
    if distance in (None, "", "정보 없음"):
        return 999999

    try:
        return int(distance)
    except (TypeError, ValueError):
        return 999999
