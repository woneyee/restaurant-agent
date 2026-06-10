import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from memory.user_memory import get_user_memory
from tools.distance_tool import sort_by_distance
from tools.rating_filter import filter_by_price, filter_by_rating, filter_by_review_count, rating_matches
from tools.restaurant_search import KNOWN_LOCATIONS, category_matches_restaurant, search_restaurants
from tools.review_analysis import filter_by_atmosphere

load_dotenv()

# ── GPT에게 알려줄 도구 명세 ──────────────────────────────────────
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": "지역과 음식 종류로 맛집을 검색합니다. 반드시 가장 먼저 호출해야 합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "검색할 지역명. 예: '전주 객사'"},
                    "category": {"type": "string", "description": "음식 종류. 예: '한식'. 없으면 생략"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_review_count",
            "description": "최소 리뷰 수 이상인 맛집만 남깁니다. 신뢰도 높은 맛집 선별에 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_reviews": {"type": "integer", "description": "최소 리뷰 개수. 보통 50~100"},
                },
                "required": ["min_reviews"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_rating",
            "description": "Planner가 추출한 사용자의 별점 조건을 검색 결과 rating에 적용합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_price",
            "description": "최대 가격대 이하인 맛집만 남깁니다. 1=저가, 2=중가, 3=고가, 4=최고가",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_price": {"type": "integer", "description": "최대 가격 레벨. 1~4"},
                },
                "required": ["max_price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_atmosphere",
            "description": "리뷰 키워드 분석으로 분위기 좋은 맛집(데이트, 친구 모임 등)만 남깁니다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sort_by_distance",
            "description": "현재 맛집 목록을 거리 기준 오름차순으로 정렬합니다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ReActAgent:
    """
    LLM(GPT-4o-mini)이 Thought → Action → Observation 루프를 직접 수행합니다.
    LLM이 어떤 도구를 언제 호출할지 스스로 판단하고, 결과를 해석해 최종 추천을 생성합니다.
    """

    def __init__(self, max_results: int = 3):
        api_key = os.getenv("GPT_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.max_results = max_results
        self.memory = get_user_memory()
        self._restaurants: list = []   # 도구 호출 사이에 공유되는 맛집 목록
        self._step = 0
        self.trace: list = []
        self._pending_thought = ""

    def run(self, state: dict) -> list:
        self._restaurants = []
        self._step = 0
        self.trace = []
        self._pending_thought = ""
        self._state = state

        print("\n" + "=" * 60)
        print("ReAct Agent: LLM 기반 Agentic workflow 시작")
        print("=" * 60)
        print(f"📥 사용자 요청: {state.get('raw_input')}")

        fav_locations = self.memory.get_favorite_locations(top_n=2)
        fav_categories = self.memory.get_favorite_categories(top_n=2)

        system_prompt = f"""당신은 맛집 추천 AI Agent입니다.
도구를 순서대로 호출하면서 사용자 조건에 맞는 맛집을 찾아주세요.

[사용자 메모리]
- 선호 위치: {fav_locations or '없음'}
- 선호 카테고리: {fav_categories or '없음'}

[도구 사용 순서]
1. search_restaurants — 반드시 첫 번째로 호출
2. filter_by_review_count — 리뷰 많은 신뢰도 높은 곳 선별
3. filter_by_rating — 별점 조건이 있을 때만 적용: {state.get('rating_conditions') or '없음'}
4. filter_by_price — 가격 조건이 있을 때만
5. filter_by_atmosphere — 분위기 조건이 있을 때만
6. sort_by_distance — 마지막에 정렬

[주의]
- 필터 후 결과가 0개면 해당 필터를 건너뛰고 다음 단계로 진행하세요
- 최종적으로 {self.max_results}개를 추천하세요
- 각 도구 호출 전에 짧게 왜 이 도구를 쓰는지 Thought를 content에 출력하세요"""

        user_message = f"""사용자 요청: "{state.get('raw_input')}"

분석된 조건:
- 위치: {state.get('location')}
- 음식 종류: {state.get('category') or '제한 없음'}
- 별점 조건: {state.get('rating_conditions') or '없음'}
- 최대 가격대: {state.get('max_price') or '제한 없음'} (1=저가~4=고가)
- 분위기 필요: {state.get('need_atmosphere')}
- 방문 목적: {state.get('purpose')}

위 조건에 맞는 맛집 {self.max_results}곳을 찾아주세요."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # ── ReAct 루프: LLM이 도구 호출을 스스로 결정 ────────────────
        for _ in range(12):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
            except Exception as error:
                print(f"\n⚠️ ReAct LLM 호출 실패: {error}. 규칙 기반 도구 실행으로 대체합니다.")
                self.trace.append({
                    "kind": "react",
                    "step": len(self.trace) + 1,
                    "thought": "LLM 호출 실패를 감지해 규칙 기반 도구 실행으로 전환합니다.",
                    "action": "fallback_to_rule_based_tools",
                    "input": {"error": str(error)},
                    "observation": "검색·필터·정렬 도구를 정해진 순서로 실행합니다.",
                })
                self._run_fallback_tools(state)
                break

            msg = response.choices[0].message
            finish = response.choices[0].finish_reason

            # LLM이 텍스트를 출력했으면 Thought로 표시
            if msg.content:
                self._step += 1
                self._pending_thought = msg.content
                print(f"\n{'─' * 60}")
                print(f"Thought {self._step}: {msg.content}")

            messages.append(msg)

            # 도구 호출 없음 → 최종 답변 완료
            if finish == "stop":
                print(f"\n{'=' * 60}")
                print("Final Answer: LLM이 생성한 최종 추천")
                print("=" * 60)
                if not self._restaurants:
                    self.trace.append({
                        "kind": "react",
                        "step": len(self.trace) + 1,
                        "thought": "LLM이 실제 도구 호출 없이 종료해 규칙 기반 실행으로 전환합니다.",
                        "action": "fallback_to_rule_based_tools",
                        "input": {},
                        "observation": "검색 후보가 없으므로 필수 도구들을 순서대로 실행합니다.",
                    })
                    self._run_fallback_tools(state)
                break

            # 도구 호출 처리
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    observation = self._execute_tool(tool_call)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": observation,
                    })

        # ── 메모리 가중치 적용 후 상위 N개 반환 ──────────────────────
        return self._select_with_memory(state)

    # ── 도구 실행 ────────────────────────────────────────────────────

    def _run_fallback_tools(self, state: dict) -> None:
        self._fallback_action(
            "search_restaurants",
            {"location": state.get("location"), "category": state.get("category")},
        )
        if state.get("rating_conditions"):
            self._fallback_action(
                "filter_by_rating",
                {"conditions": state.get("rating_conditions")},
            )

        if state.get("max_price") is not None:
            self._fallback_action("filter_by_price", {"max_price": state.get("max_price")})
        if state.get("need_atmosphere"):
            self._fallback_action("filter_by_atmosphere", {})

        self._fallback_action("sort_by_distance", {})

    def _fallback_action(self, name: str, args: dict) -> None:
        self._pending_thought = f"규칙 기반 fallback에서 {name} 도구를 실행합니다."
        observation = self._dispatch(name, args)
        self._record_trace(name, args, observation)

    def _execute_tool(self, tool_call) -> str:
        self._step += 1
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments or "{}")
        if name == "search_restaurants":
            args = {
                "location": self._state.get("location") or args.get("location"),
                "category": self._state.get("category"),
            }

        print(f"\n{'─' * 60}")
        print(f"Action {self._step}: [{name}] 도구 호출")
        print(f"   입력값: {args}")

        try:
            observation = self._dispatch(name, args)
        except Exception as error:
            observation = f"도구 실행 실패: {error}. 이 단계를 건너뜁니다."

        self._record_trace(name, args, observation)
        print(f"Observation {self._step}: {observation}")
        return observation

    def _record_trace(self, name: str, args: dict, observation: str) -> None:
        self.trace.append({
            "kind": "react",
            "step": len(self.trace) + 1,
            "thought": self._pending_thought or f"{name} 도구가 필요하다고 판단했습니다.",
            "action": name,
            "input": args,
            "observation": observation,
        })
        self._pending_thought = ""

    def _dispatch(self, name: str, args: dict) -> str:
        if name == "search_restaurants":
            location = self._state.get("location") or args.get("location")
            category = self._state.get("category")
            self._restaurants = search_restaurants(
                location=location,
                category=category,
            )
            if not self._restaurants:
                return (
                    "검색 결과 없음. 지역명이나 음식 종류를 확인하거나 조건을 완화하세요. "
                    f"대안 지역: {', '.join(KNOWN_LOCATIONS)}"
                )
            summary = _summarize(self._restaurants[:3])
            return f"검색 완료: {len(self._restaurants)}개 발견. 예시: {summary}"

        if name == "filter_by_review_count":
            filtered = filter_by_review_count(
                self._restaurants, min_reviews=args.get("min_reviews", 50)
            )
            if filtered:
                self._restaurants = filtered
                return f"리뷰 수 필터 완료: {len(self._restaurants)}개 남음"
            return f"리뷰 수 {args.get('min_reviews')}개 미만 결과 없음. 필터 건너뜁니다 ({len(self._restaurants)}개 유지)"

        if name == "filter_by_rating":
            conditions = self._state.get("rating_conditions") or []
            if not conditions:
                return "사용자 별점 조건이 없어 별점 필터를 스킵합니다."
            filtered = filter_by_rating(self._restaurants, conditions)
            if filtered:
                self._restaurants = filtered
                return f"별점 필터 완료: {len(self._restaurants)}개 남음. {_summarize(self._restaurants[:3])}"
            self._restaurants = []
            return f"별점 조건 {conditions}에 맞는 결과 없음"

        if name == "filter_by_price":
            max_price = self._state.get("max_price")
            if max_price is None:
                return "사용자 가격 조건이 없어 가격 필터를 스킵합니다."
            filtered = filter_by_price(
                self._restaurants, max_price=max_price
            )
            if filtered:
                self._restaurants = filtered
                return f"가격 필터 완료: {len(self._restaurants)}개 남음"
            return f"가격대 {args.get('max_price')} 이하 결과 없음. 필터 건너뜁니다 ({len(self._restaurants)}개 유지)"

        if name == "filter_by_atmosphere":
            if not self._state.get("need_atmosphere"):
                return "사용자 분위기 조건이 없어 분위기 필터를 스킵합니다."
            filtered = filter_by_atmosphere(self._restaurants)
            if filtered:
                self._restaurants = filtered
                return f"분위기 필터 완료: {len(self._restaurants)}개 남음"
            return f"분위기 키워드 매칭 결과 없음. 필터 건너뜁니다 ({len(self._restaurants)}개 유지)"

        if name == "sort_by_distance":
            self._restaurants = sort_by_distance(self._restaurants)
            return f"거리 정렬 완료: {len(self._restaurants)}개"

        return f"알 수 없는 도구: {name}"

    # ── 메모리 가중치 적용 및 최종 선택 ─────────────────────────────

    def _select_with_memory(self, state: dict) -> list:
        conditions = state.get("rating_conditions") or []
        self._restaurants = [
            restaurant
            for restaurant in self._restaurants
            if rating_matches(restaurant.get("rating"), conditions)
            and category_matches_restaurant(restaurant, state.get("category"))
        ]

        if not self._restaurants:
            print("\n❌ 조건에 맞는 맛집이 없습니다.")
            return []

        for r in self._restaurants:
            r["memory_weight"] = self.memory.should_recommend_by_memory(
                location=r.get("location", ""),
                category=r.get("category", ""),
                rating=_safe_float(r.get("rating")),
            )

        ranked = sorted(
            self._restaurants,
            key=lambda r: (r.get("memory_weight", 1.0), _safe_float(r.get("rating"))),
            reverse=True,
        )

        recommendations = ranked[: self.max_results]
        _add_reasons(recommendations, state)
        return recommendations


# ── 유틸 ─────────────────────────────────────────────────────────

def _summarize(restaurants: list) -> str:
    if not restaurants:
        return "없음"
    parts = [
        f"{r.get('name')}(별점:{r.get('rating')}, 리뷰:{r.get('review_count')}, 가격:{r.get('price_level')})"
        for r in restaurants
    ]
    return ", ".join(parts)


def _add_reasons(restaurants: list, state: dict) -> None:
    for r in restaurants:
        reasons = []
        rating = _safe_float(r.get("rating"))
        review_count = _safe_int(r.get("review_count"))
        if rating >= 4.5:
            reasons.append(f"✓ 높은 별점 ({r.get('rating')}점)")
        elif rating >= 4.0:
            reasons.append(f"✓ 우수 별점 ({r.get('rating')}점)")
        if review_count >= 200:
            reasons.append(f"✓ 리뷰 다수 ({r.get('review_count')}개)")
        max_price = _safe_int(state.get("max_price"), default=0)
        price_level = _safe_int(r.get("price_level"), default=99)
        if max_price and price_level <= max_price:
            reasons.append("✓ 가격대 적합")
        if r.get("is_good_atmosphere"):
            reasons.append("✓ 분위기 좋음")
        w = r.get("memory_weight", 1.0)
        if w > 1.1:
            reasons.append(f"★ 선호도 보너스 (+{int((w - 1) * 100)}%)")
        r["recommend_reason"] = " / ".join(reasons) if reasons else "조건에 잘 맞는 맛집"


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
