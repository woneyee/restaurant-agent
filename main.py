import sys

from agents.graph_agent import build_restaurant_graph
from memory.user_memory import get_user_memory


def configure_console_encoding():
    """Windows 터미널에서 한글 입출력이 깨지는 문제를 줄입니다."""
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def print_final_recommendations(final_state):
    recommendations = final_state.get("recommendations", [])

    print("\n" + "="*70)
    print("✨ 최종 추천 결과")
    print("="*70)

    if not recommendations:
        print("조건에 맞는 맛집을 찾지 못했습니다. 위치나 조건을 바꿔 다시 시도해주세요.")
        return

    for index, restaurant in enumerate(recommendations, start=1):
        print(f"\n{index}. 🍽️  {restaurant.get('name')}")
        print(f"   📍 주소: {restaurant.get('address', '정보 없음')}")
        print(f"   🏷️  카테고리: {restaurant.get('category', '정보 없음')}")
        print(f"   ⭐ 별점: {restaurant.get('rating', '정보 없음')}/5.0 "
              f"({restaurant.get('review_count', 0)}개 리뷰)")
        price_level = restaurant.get("price_level")
        print(f"   💰 가격대: {'$' * price_level if price_level else '정보 없음'}")
        print(f"   📏 거리: {restaurant.get('distance', '정보 없음')}")
        print(f"   ✨ 추천 이유: {restaurant.get('recommend_reason', '조건에 잘 맞습니다')}")

    print("\n" + "="*70)


def main():
    configure_console_encoding()

    print("\n" + "="*70)
    print("🤖 LangGraph Supervisor: 맛집 추천 AI Agent")
    print("="*70)
    print("원하는 음식과 분위기를 말하면 딱 맞는 맛집을 찾아드려요.")
    print("\n📝 예시 입력:")
    print("  - 전주 객사에서 분위기 좋은 한식 맛집 찾아줘")
    print("  - 전주 한옥마을 근처 저렴한 카페")
    print("  - 친구랑 저녁 먹기 좋은 일식당")
    print("─"*70)

    user_input = input("\n💬 User Input: ").strip()

    if not user_input:
        print("\n❌ Supervisor: 입력이 비어 있어 종료합니다.")
        return

    try:
        graph = build_restaurant_graph()
    except ModuleNotFoundError as error:
        print(f"\n❌ Supervisor Observation: {error}")
        print("   설치 방법: pip install langgraph")
        return

    initial_state = {
        "user_input": user_input,
        "recommendations": [],
        "need_retry": False,
        "reflection_reason": "",
        "retry_count": 0,
    }

    print("\n🔄 Supervisor Action:")
    print("LangGraph workflow를 실행합니다...")

    final_state = graph.invoke(initial_state)
    print_final_recommendations(final_state)

    # 메모리 요약 출력
    memory = get_user_memory()
    if memory.get_visit_count() > 0:
        print("\n📊 사용자 방문 기록:")
        memory.print_summary()

    print("🏁 Supervisor: Agentic workflow 종료")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
