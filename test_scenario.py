# -*- coding: utf-8 -*-
"""
테스트 시나리오: 단계별 Trace 확인용 스크립트
입력: "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘.
      너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘."
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from agents.graph_agent import build_restaurant_graph
from memory.user_memory import get_user_memory

USER_INPUT = (
    "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. "
    "너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘."
)


def print_final_recommendations(final_state):
    recommendations = final_state.get("recommendations", [])
    print("\n" + "=" * 70)
    print("최종 추천 결과")
    print("=" * 70)

    if not recommendations:
        print("조건에 맞는 맛집을 찾지 못했습니다. 위치나 조건을 바꿔 다시 시도해주세요.")
        return

    for index, restaurant in enumerate(recommendations, start=1):
        print(f"\n{index}. {restaurant.get('name')}")
        print(f"   주소: {restaurant.get('address', '정보 없음')}")
        print(f"   카테고리: {restaurant.get('category', '정보 없음')}")
        print(f"   별점: {restaurant.get('rating', '정보 없음')}/5.0 "
              f"({restaurant.get('review_count', 0)}개 리뷰)")
        price_level = restaurant.get("price_level")
        print(f"   가격대: {'$' * price_level if price_level else '정보 없음'}")
        print(f"   거리: {restaurant.get('distance', '정보 없음')}m")
        print(f"   추천 이유: {restaurant.get('recommend_reason', '조건에 잘 맞습니다')}")

    print("\n" + "=" * 70)


def main():
    print("\n" + "=" * 70)
    print("LangGraph Supervisor: 맛집 추천 AI Agent - 테스트 시나리오")
    print("=" * 70)
    print(f"User Input: {USER_INPUT}")
    print("=" * 70)

    graph = build_restaurant_graph()

    initial_state = {
        "user_input": USER_INPUT,
        "recommendations": [],
        "need_retry": False,
        "reflection_reason": "",
        "retry_count": 0,
    }

    final_state = graph.invoke(initial_state)
    print_final_recommendations(final_state)

    memory = get_user_memory()
    if memory.get_visit_count() > 0:
        memory.print_summary()

    print("Agentic workflow 종료")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
