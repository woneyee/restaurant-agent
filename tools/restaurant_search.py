import os
import json
from pathlib import Path
from math import asin, cos, radians, sin, sqrt

import requests
from dotenv import load_dotenv


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GOOGLE_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

CATEGORY_PLACE_TYPES = {
    "카페": {"cafe", "coffee_shop"},
    "디저트": {"bakery", "cafe", "dessert_shop"},
    "술집": {"bar", "night_club"},
}

# 샘플 데이터 경로
SAMPLE_DATA_PATH = Path(__file__).parent.parent / "data" / "restaurants.json"


def search_restaurants(location, category=None):
    """
    Google Places Text Search API를 사용해 맛집을 검색합니다.
    API 키가 없으면 샘플 데이터를 사용합니다.

    반환 형식:
    [
        {
            "name": "...",
            "rating": 4.5,
            "review_count": 312,
            "price_level": 2,
            "address": "...",
            "location": "...",
            "reviews": []
        }
    ]
    """
    print("[Tool] restaurant_search 시작")
    print(f"[Tool] 입력: location='{location}', category='{category}'")

    # API 키 확인
    if not GOOGLE_API_KEY:
        print("[Tool] ⚠️ GOOGLE_API_KEY가 없습니다. 샘플 데이터를 사용합니다.")
        return _load_sample_data(location, category)

    query = _build_query(location, category)
    print(f"[Tool] Google Places 쿼리: '{query}'")

    params = {
        "query": query,
        "language": "ko",
        "key": GOOGLE_API_KEY,
    }

    try:
        response = requests.get(
            GOOGLE_PLACES_TEXT_SEARCH_URL,
            params=params,
            timeout=10,
        )
    except requests.RequestException as error:
        print(f"[Tool] ❌ Google Places API 요청 실패: {error}")
        print("[Tool] 샘플 데이터로 대체합니다.")
        return _load_sample_data(location, category)

    print(f"[Tool] HTTP Status: {response.status_code}")

    try:
        data = response.json()
    except ValueError as error:
        print(f"[Tool] ❌ JSON 파싱 실패: {error}")
        print("[Tool] 샘플 데이터로 대체합니다.")
        return _load_sample_data(location, category)

    google_status = data.get("status")
    print(f"[Tool] Google API Status: {google_status}")

    if response.status_code != 200:
        print(f"[Tool] ❌ HTTP 오류: {response.status_code}")
        print("[Tool] 샘플 데이터로 대체합니다.")
        return _load_sample_data(location, category)

    if google_status not in ("OK", "ZERO_RESULTS"):
        print(f"[Tool] ❌ Google API 오류: {google_status}")
        if "error_message" in data:
            print(f"[Tool] 오류 메시지: {data.get('error_message')}")
        print("[Tool] 샘플 데이터로 대체합니다.")
        return _load_sample_data(location, category)

    if google_status == "ZERO_RESULTS":
        print("[Tool] ⚠️ 검색 결과 없음")
        print("[Tool] 샘플 데이터로 대체합니다.")
        return _load_sample_data(location, category)

    origin = _geocode_location(location)
    restaurants = [
        _normalize_place(place, location, origin, category)
        for place in data.get("results", [])
        if category_matches_place(place, category)
    ]

    print(f"[Tool] ✅ 검색 결과: {len(restaurants)}개")
    return restaurants


KNOWN_LOCATIONS = ["전주 객사", "전주 한옥마을", "전북대"]


def _is_unknown_location(location: str, all_restaurants: list) -> bool:
    """샘플 데이터에 전혀 없는 지역인지 확인합니다."""
    return not any(
        location.lower() in r.get("location", "").lower()
        for r in all_restaurants
    )


def _load_sample_data(location, category):
    """샘플 데이터를 로드하고 필터링합니다."""
    try:
        if not SAMPLE_DATA_PATH.exists():
            print(f"[Tool] ❌ 샘플 데이터 파일 없음: {SAMPLE_DATA_PATH}")
            return []

        with open(SAMPLE_DATA_PATH, "r", encoding="utf-8") as f:
            all_restaurants = json.load(f)

        # 존재하지 않는 지역 감지
        if _is_unknown_location(location, all_restaurants):
            print(f"[Tool] ⚠️ 알 수 없는 지역: '{location}'")
            print(f"[Tool] 지원 지역: {', '.join(KNOWN_LOCATIONS)}")
            print(f"[Tool] 예외 처리: 검색 결과 없음으로 반환합니다.")
            return []

        # 위치 기반 필터링
        filtered = [r for r in all_restaurants if location.lower() in r.get("location", "").lower()]

        # 카테고리 기반 필터링
        if category:
            cat_filtered = [r for r in filtered if category.lower() in r.get("category", "").lower()]
            if not cat_filtered:
                print(f"[Tool] ⚠️ '{location}'에서 '{category}' 카테고리 결과 없음.")
                filtered = []
            else:
                filtered = cat_filtered

        print(f"[Tool] ✅ 샘플 데이터 로드: {len(filtered)}개 (위치: {location}, 카테고리: {category or '전체'})")
        return filtered

    except (json.JSONDecodeError, IOError) as error:
        print(f"[Tool] ❌ 샘플 데이터 로드 실패: {error}")
        return []


def _build_query(location, category=None):
    query_parts = []

    if location:
        query_parts.append(location.strip())

    if category:
        query_parts.append(category.strip())

    query_parts.append("맛집")
    return " ".join(query_parts)


def _normalize_place(place, requested_location, origin=None, requested_category=None):
    # rating/review_count: None이면 0으로 변환 (필터 비교 시 TypeError 방지)
    # price_level: None 그대로 유지 (0과 구분해 "정보 없음" 처리)
    raw_rating = place.get("rating")
    raw_reviews = place.get("user_ratings_total")
    raw_price = place.get("price_level")

    coordinates = place.get("geometry", {}).get("location", {})

    return {
        "name": place.get("name", "이름 없음"),
        "place_id": place.get("place_id"),
        "category": requested_category or _category_from_types(place.get("types") or []),
        "rating": float(raw_rating) if raw_rating is not None else 0.0,
        "review_count": int(raw_reviews) if raw_reviews is not None else 0,
        "price_level": int(raw_price) if raw_price is not None else None,
        "address": place.get("formatted_address", "주소 정보 없음"),
        "location": requested_location,
        "reviews": [],
        "place_types": place.get("types") or [],
        "distance": _calculate_distance(origin, coordinates),
    }


def category_matches_place(place, requested_category):
    """Google 장소 유형으로 검증 가능한 카테고리는 엄격하게 일치시킵니다."""
    if not requested_category:
        return True

    expected_types = CATEGORY_PLACE_TYPES.get(requested_category)
    if not expected_types:
        return True

    place_types = set(place.get("types") or [])
    return bool(place_types & expected_types)


def category_matches_restaurant(restaurant, requested_category):
    if not requested_category:
        return True
    return restaurant.get("category") == requested_category


def _category_from_types(place_types):
    types = set(place_types)
    for category, expected_types in CATEGORY_PLACE_TYPES.items():
        if types & expected_types:
            return category
    return "음식점"


def enrich_place_reviews(restaurants, limit=8):
    """Google Place Details에서 실제 리뷰를 제한적으로 보강합니다."""
    if not GOOGLE_API_KEY:
        return restaurants

    fetched = 0
    for restaurant in restaurants:
        if restaurant.get("reviews") or not restaurant.get("place_id") or fetched >= limit:
            continue
        fetched += 1
        try:
            response = requests.get(
                GOOGLE_PLACE_DETAILS_URL,
                params={
                    "place_id": restaurant["place_id"],
                    "fields": "reviews",
                    "language": "ko",
                    "key": GOOGLE_API_KEY,
                },
                timeout=5,
            )
            data = response.json()
            if response.status_code == 200 and data.get("status") == "OK":
                restaurant["reviews"] = [
                    review.get("text", "")
                    for review in data.get("result", {}).get("reviews", [])
                    if review.get("text")
                ]
        except (requests.RequestException, ValueError):
            continue

    return restaurants


def _geocode_location(location):
    if not GOOGLE_API_KEY or not location:
        return None

    try:
        response = requests.get(
            GOOGLE_GEOCODING_URL,
            params={"address": location, "language": "ko", "key": GOOGLE_API_KEY},
            timeout=10,
        )
        data = response.json()
        if response.status_code == 200 and data.get("status") == "OK":
            return data["results"][0]["geometry"]["location"]
    except (requests.RequestException, ValueError, KeyError, IndexError):
        pass

    return None


def _calculate_distance(origin, destination):
    if not origin or not destination:
        return "정보 없음"

    lat1, lon1 = radians(origin["lat"]), radians(origin["lng"])
    lat2, lon2 = radians(destination["lat"]), radians(destination["lng"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(6371000 * 2 * asin(sqrt(value)))
