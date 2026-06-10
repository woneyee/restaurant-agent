import json
import os
from datetime import datetime
from pathlib import Path


class UserMemory:
    """사용자의 맛집 선호도와 방문 이력을 관리합니다."""

    def __init__(self, memory_file: str = None):
        if memory_file is None:
            memory_file = Path(__file__).parent / "user_preferences.json"
        
        self.memory_file = memory_file
        self.data = self._load_memory()

    def _load_memory(self) -> dict:
        """메모리 파일에서 사용자 데이터를 로드합니다."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._init_memory()
        return self._init_memory()

    def _init_memory(self) -> dict:
        """초기 메모리 구조를 생성합니다."""
        return {
            "favorite_categories": {},  # {"한식": 5, "일식": 3}
            "favorite_locations": {},   # {"전주 객사": 4, "전주 한옥마을": 2}
            "price_preferences": {"average": 2},  # 1=싼맛, 2=중간, 3=비싼맛
            "visit_history": [],  # [{"restaurant": "...", "date": "...", "rating": 5}]
            "total_visits": 0,
        }

    def _save_memory(self) -> None:
        """메모리를 파일에 저장합니다."""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def record_visit(
        self,
        restaurant_name: str,
        location: str,
        category: str,
        user_rating: int = 5,
    ) -> None:
        """맛집 방문 이력을 기록합니다."""
        visit = {
            "restaurant": restaurant_name,
            "location": location,
            "category": category,
            "rating": user_rating,
            "date": datetime.now().isoformat(),
        }
        
        self.data["visit_history"].append(visit)
        self.data["total_visits"] += 1

        # 카테고리 선호도 업데이트
        self.data["favorite_categories"][category] = (
            self.data["favorite_categories"].get(category, 0) + user_rating
        )

        # 위치 선호도 업데이트
        self.data["favorite_locations"][location] = (
            self.data["favorite_locations"].get(location, 0) + 1
        )

        self._save_memory()

    def record_price_preference(self, price_level: int) -> None:
        """사용자의 가격대 선호도를 업데이트합니다."""
        current_avg = self.data["price_preferences"]["average"]
        total = self.data["total_visits"]
        
        # 이동 평균 계산
        new_avg = (current_avg * total + price_level) / (total + 1)
        self.data["price_preferences"]["average"] = round(new_avg, 2)
        
        self._save_memory()

    def get_favorite_categories(self, top_n: int = 3) -> list:
        """상위 N개의 선호 카테고리를 반환합니다."""
        sorted_categories = sorted(
            self.data["favorite_categories"].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [cat[0] for cat in sorted_categories[:top_n]]

    def get_favorite_locations(self, top_n: int = 3) -> list:
        """상위 N개의 선호 위치를 반환합니다."""
        sorted_locations = sorted(
            self.data["favorite_locations"].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [loc[0] for loc in sorted_locations[:top_n]]

    def get_price_preference(self) -> int:
        """사용자의 평균 가격대 선호도를 반환합니다."""
        return int(self.data["price_preferences"]["average"])

    def get_visit_count(self, restaurant_name: str = None) -> int:
        """특정 맛집의 방문 횟수를 반환합니다. None이면 전체 방문 횟수."""
        if restaurant_name is None:
            return self.data["total_visits"]
        
        return len(
            [v for v in self.data["visit_history"]
             if v["restaurant"] == restaurant_name]
        )

    def get_recent_visits(self, days: int = 30, top_n: int = 5) -> list:
        """최근 N일 이내의 방문 기록을 반환합니다."""
        now = datetime.now()
        recent = []
        
        for visit in self.data["visit_history"]:
            visit_date = datetime.fromisoformat(visit["date"])
            if (now - visit_date).days <= days:
                recent.append(visit)
        
        # 최신순 정렬 후 상위 N개
        return sorted(
            recent,
            key=lambda x: x["date"],
            reverse=True,
        )[:top_n]

    def should_recommend_by_memory(
        self,
        location: str,
        category: str,
        rating: float,
    ) -> float:
        """
        메모리 기반으로 추천 가중치를 계산합니다.
        0.8 ~ 1.5 범위의 가중치를 반환합니다.
        """
        weight = 1.0

        # 선호 위치 보너스
        if location in self.data["favorite_locations"]:
            location_score = self.data["favorite_locations"][location]
            weight += (location_score / 10) * 0.3  # 최대 +0.3

        # 선호 카테고리 보너스
        if category in self.data["favorite_categories"]:
            category_score = self.data["favorite_categories"][category]
            weight += (category_score / 10) * 0.2  # 최대 +0.2

        # 높은 별점 보너스
        if rating >= 4.5:
            weight += 0.2
        elif rating >= 4.0:
            weight += 0.1

        return min(weight, 1.5)  # 최대 1.5배

    def print_summary(self) -> None:
        """사용자 메모리 요약을 출력합니다."""
        print("\n================ User Memory Summary ================")
        print(f"총 방문 횟수: {self.data['total_visits']}회")
        
        if self.data["favorite_categories"]:
            print(f"선호 카테고리: {', '.join(self.get_favorite_categories())}")
        
        if self.data["favorite_locations"]:
            print(f"선호 위치: {', '.join(self.get_favorite_locations())}")
        
        print(f"평균 가격대 선호: {self.get_price_preference()}단계")
        
        recent = self.get_recent_visits(top_n=3)
        if recent:
            print("\n최근 방문:")
            for visit in recent:
                print(f"  - {visit['restaurant']} ({visit['location']}) "
                      f"⭐{visit['rating']}/5")
        
        print("====================================================\n")

    def clear_memory(self) -> None:
        """모든 메모리 데이터를 삭제합니다."""
        self.data = self._init_memory()
        self._save_memory()


# 전역 메모리 인스턴스
_global_memory = None


def get_user_memory() -> UserMemory:
    """전역 UserMemory 인스턴스를 반환합니다."""
    global _global_memory
    if _global_memory is None:
        _global_memory = UserMemory()
    return _global_memory


def reset_user_memory() -> None:
    """전역 메모리를 초기화합니다."""
    global _global_memory
    _global_memory = None
