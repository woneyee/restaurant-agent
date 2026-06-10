from typing import Any, Dict, List, Optional, TypedDict

from agents.planner import PlannerAgent
from agents.react_agent import ReActAgent
from agents.reflection_agent import ReflectionAgent


class RestaurantState(TypedDict, total=False):
    """LangGraph에서 노드들이 공유하는 상태입니다."""

    user_input: str
    raw_input: str
    location: Optional[str]
    category: Optional[str]
    rating_conditions: List[Dict[str, Any]]
    max_price: Optional[int]
    need_atmosphere: bool
    purpose: str
    recommendations: List[Dict[str, Any]]
    need_retry: bool
    reflection_reason: str
    retry_count: int


def build_restaurant_graph():
    """
    Supervisor 흐름을 LangGraph로 정의합니다.

    Graph:
    planner -> ask_user or react -> reflection -> fallback or final
    """
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "langgraph가 설치되어 있지 않습니다. "
            "다음 명령으로 설치해주세요: py -m pip install langgraph"
        ) from error

    graph = StateGraph(RestaurantState)

    graph.add_node("planner", planner_node)
    graph.add_node("ask_user", ask_user_node)
    graph.add_node("react", react_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("final", final_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "ask_user": "ask_user",
            "react": "react",
        },
    )
    graph.add_edge("ask_user", "react")
    graph.add_edge("react", "reflection")
    graph.add_conditional_edges(
        "reflection",
        route_after_reflection,
        {
            "fallback": "fallback",
            "final": "final",
        },
    )
    graph.add_edge("fallback", "react")
    graph.add_edge("final", END)

    return graph.compile()


def planner_node(state: RestaurantState) -> RestaurantState:
    print("\n[LangGraph Node] planner")
    print("Supervisor Thought: 사용자 요청을 구조화된 state로 변환합니다.")

    planner = PlannerAgent()
    planned_state = planner.plan(state["user_input"])

    return {
        **state,
        **planned_state,
        "recommendations": [],
        "need_retry": False,
        "reflection_reason": "",
        "retry_count": state.get("retry_count", 0),
    }


def ask_user_node(state: RestaurantState) -> RestaurantState:
    print("\n[LangGraph Node] ask_user")
    print("Supervisor Thought: 요청이 모호하므로 사용자에게 추가 조건을 질문합니다.")

    updated_state = dict(state)

    if not updated_state.get("location"):
        location = input(
            "원하는 지역/위치를 입력해주세요. 예: 전주 객사\n지역: "
        ).strip()
        updated_state["location"] = location or "전주 객사"

    if not updated_state.get("category"):
        category = input(
            "원하는 음식 종류를 입력해주세요. 예: 한식, 양식, 일식, 카페, 술집, 디저트\n음식 종류: "
        ).strip()
        updated_state["category"] = category or None

    updated_state["raw_input"] = (
        f"{updated_state.get('raw_input', '')} "
        f"지역: {updated_state.get('location')} "
        f"음식 종류: {updated_state.get('category') or '전체'}"
    ).strip()

    print("\nSupervisor Observation:")
    print(f"보완된 state={updated_state}")

    return updated_state


def react_node(state: RestaurantState) -> RestaurantState:
    print("\n[LangGraph Node] react")
    print("Supervisor Action: ReAct Agent를 실행합니다.")

    react_agent = ReActAgent(max_results=3)
    recommendations = react_agent.run(state)

    return {
        **state,
        "recommendations": recommendations,
    }


def reflection_node(state: RestaurantState) -> RestaurantState:
    print("\n[LangGraph Node] reflection")
    print("Supervisor Action: Reflection Agent로 추천 결과를 검토합니다.")

    reflection_agent = ReflectionAgent()
    reflection = reflection_agent.reflect(
        state.get("recommendations", []),
        state,
    )

    return {
        **state,
        "need_retry": reflection["need_retry"],
        "reflection_reason": reflection["reason"],
    }


def fallback_node(state: RestaurantState) -> RestaurantState:
    print("\n[LangGraph Node] fallback")
    print("Supervisor Thought: 조건을 완화하여 재검색합니다.")
    print(f"Retry reason: {state.get('reflection_reason')}")

    retry_count = state.get("retry_count", 0) + 1

    return {
        **state,
        "max_price": None,
        "need_atmosphere": False,
        "retry_count": retry_count,
        "need_retry": False,
    }


def final_node(state: RestaurantState) -> RestaurantState:
    print("\n[LangGraph Node] final")
    print("Supervisor Observation: 최종 추천 상태에 도달했습니다.")
    return state


def route_after_planner(state: RestaurantState) -> str:
    if not state.get("location"):
        print("[LangGraph Route] planner -> ask_user")
        return "ask_user"

    print("[LangGraph Route] planner -> react")
    return "react"


def route_after_reflection(state: RestaurantState) -> str:
    if state.get("need_retry") and state.get("retry_count", 0) < 1:
        print("[LangGraph Route] reflection -> fallback")
        return "fallback"

    print("[LangGraph Route] reflection -> final")
    return "final"
