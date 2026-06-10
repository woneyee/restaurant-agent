from pathlib import Path
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.planner import PlannerAgent
from agents.react_agent import ReActAgent
from agents.reflection_agent import ReflectionAgent


BASE_DIR = Path(__file__).resolve().parent
DESIGN_DIR = BASE_DIR / "design"

app = FastAPI(title="Restaurant Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_ui_cache(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.endswith((".html", ".jsx", ".css")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


class RecommendRequest(BaseModel):
    query: str


@app.post("/api/recommend")
def recommend(request: RecommendRequest):
    print("\n" + "="*70)
    print("API /api/recommend 호출")
    print("="*70)
    print(f"📥 사용자 쿼리: {request.query}")

    planner = PlannerAgent()
    react_agent = ReActAgent(max_results=3)
    reflection_agent = ReflectionAgent()

    # 1. 플래닝 단계
    state = planner.plan(request.query)
    planned_state = state.copy()

    # 위치 정보 누락 확인
    if not state.get("location"):
        clarification_msg = "원하는 지역/위치 정보가 없습니다."
        print(f"\n⚠️ {clarification_msg}")
        
        questions = state.get("clarification_questions", [])
        if not questions:
            questions = ["원하는 지역/위치를 입력해주세요. 예: 전주 객사, 전주 한옥마을"]
        
        return {
            "status": "need_more_info",
            "message": clarification_msg,
            "questions": questions,
            "missing_fields": ["location"],
            "state": state,
            "trace": _build_need_more_info_trace(state, questions),
            "recommendations": [],
            "used_fallback": False,
        }

    # 2. ReAct 단계
    print("\n[API] ReAct Agent 실행...")
    recommendations = react_agent.run(state)
    first_react_trace = list(react_agent.trace)

    # 3. Reflection 단계
    print("\n[API] Reflection Agent 실행...")
    reflection = reflection_agent.reflect(recommendations, state)

    used_fallback = False
    fallback_event = None
    retry_react_trace = []

    # 4. Fallback 단계 (필요 시)
    if reflection["need_retry"]:
        print("\n[API] Fallback: 조건 완화 후 재시도")
        used_fallback = True
        original_state = state.copy()
        retry_state = state.copy()
        retry_state["max_price"] = None
        retry_state["need_atmosphere"] = False
        fallback_event = {
            "kind": "fallback",
            "from": _condition_summary(original_state),
            "to": _condition_summary(retry_state),
            "reason": reflection.get("reason"),
        }
        recommendations = react_agent.run(retry_state)
        retry_react_trace = list(react_agent.trace)
        reflection = reflection_agent.reflect(recommendations, retry_state)
        state = retry_state

    # 5. UI 변환
    ui_results = [
        _to_ui_place(restaurant, index)
        for index, restaurant in enumerate(recommendations, start=1)
    ]

    print("\n[API] 응답 생성 완료")
    print("="*70 + "\n")

    response_payload = {
        "status": "ok",
        "message": (
            f"{len(ui_results)}개의 맛집을 추천합니다."
            if ui_results
            else "조건에 맞는 결과가 없습니다. 지역이나 가격·분위기 조건을 완화해 다시 시도해 주세요."
        ),
        "alternatives": [] if ui_results else [
            "음식 종류 조건을 제거해 보세요.",
            "가격대 또는 분위기 조건을 완화해 보세요.",
            "전주 객사, 전주 한옥마을, 전북대 중 한 지역을 선택해 보세요.",
        ],
        "state": state,
        "requested_state": planned_state,
        "reflection": reflection,
        "recommendations": ui_results,
        "used_fallback": used_fallback,
        "trace": _build_trace(
            planned_state,
            recommendations,
            reflection,
            first_react_trace,
            fallback_event,
            retry_react_trace,
        ),
    }
    _save_submission_trace(request.query, response_payload)
    return response_payload


def _build_need_more_info_trace(state, questions):
    return [
        {
            "kind": "bot",
            "text": "요청을 분석했는데 필수 정보가 부족해요.",
        },
        {
            "kind": "planner",
            "state": state,
            "clarification_needed": True,
            "questions": questions,
        },
        {
            "kind": "bot",
            "text": "다시 시도해 주세요: " + questions[0] if questions else "원하는 지역을 알려주세요.",
        },
    ]


def _build_trace(
    planned_state,
    recommendations,
    reflection,
    first_react_trace,
    fallback_event=None,
    retry_react_trace=None,
):
    """실제 실행 중 수집한 제출용 Trace를 반환합니다."""
    trace = [{
        "kind": "planner",
        "state": planned_state,
        "thought": "사용자 요청을 검색 조건으로 구조화합니다.",
        "action": "PlannerAgent.plan",
        "observation": _condition_summary(planned_state),
    }]
    trace.extend(first_react_trace)
    if fallback_event:
        trace.append({
            "kind": "reflect",
            "text": fallback_event.get("reason") or "추천 결과 보완이 필요합니다.",
        })
        trace.append(fallback_event)
        trace.extend(retry_react_trace or [])
    trace.append({
        "kind": "reflect",
        "text": reflection.get("reason", "추천 결과 검토 완료"),
    })
    trace.append({
        "kind": "final_answer",
        "recommendations": len(recommendations),
        "summary": f"{len(recommendations)}개의 맛집을 추천합니다",
    })

    return trace


def _condition_summary(state):
    return {
        "location": state.get("location"),
        "category": state.get("category"),
        "rating": _rating_condition_label(state),
        "price": (
            f"<= {state.get('max_price')}"
            if state.get("max_price") is not None
            else "무제한"
        ),
        "max_price": state.get("max_price"),
        "atmosphere": state.get("need_atmosphere"),
        "need_atmosphere": state.get("need_atmosphere"),
        "purpose": state.get("purpose"),
    }


def _save_submission_trace(query, payload):
    trace_path = BASE_DIR / "logs" / "submission_trace.json"
    markdown_path = BASE_DIR / "logs" / "submission_trace.md"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    submission = {
        "query": query,
        "requested_state": payload.get("requested_state"),
        "state": payload.get("state"),
        "trace": payload.get("trace"),
        "recommendations": payload.get("recommendations"),
        "alternatives": payload.get("alternatives"),
    }
    trace_path.write_text(
        json.dumps(submission, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(_submission_markdown(submission), encoding="utf-8")


def _submission_markdown(submission):
    lines = [
        "# 맛집 추천 Agent 실행 Trace",
        "",
        f"**사용자 요청:** {submission.get('query')}",
        "",
        "## 단계별 실행",
        "",
    ]

    for event in submission.get("trace") or []:
        kind = event.get("kind")
        if kind == "planner":
            lines.extend([
                "### Planner",
                f"- Thought: {event.get('thought')}",
                f"- Action: `{event.get('action')}`",
                f"- Observation: `{json.dumps(event.get('observation'), ensure_ascii=False)}`",
                "",
            ])
        elif kind == "react":
            lines.extend([
                f"### ReAct Step {event.get('step')}",
                f"- Thought: {event.get('thought')}",
                f"- Action: `{event.get('action')}`",
                f"- Input: `{json.dumps(event.get('input'), ensure_ascii=False)}`",
                f"- Observation: {event.get('observation')}",
                "",
            ])
        elif kind == "reflect":
            lines.extend(["### Reflection", f"- Observation: {event.get('text')}", ""])
        elif kind == "fallback":
            lines.extend([
                "### Fallback",
                f"- Reason: {event.get('reason')}",
                f"- From: `{json.dumps(event.get('from'), ensure_ascii=False)}`",
                f"- To: `{json.dumps(event.get('to'), ensure_ascii=False)}`",
                "",
            ])

    lines.extend(["## 최종 추천", ""])
    for index, item in enumerate(submission.get("recommendations") or [], start=1):
        lines.append(
            f"{index}. **{item.get('name')}** - 별점 {item.get('rating')}, "
            f"리뷰 {item.get('user_ratings_total')}개, 거리 {item.get('distance_m')}m, "
            f"가격대 {item.get('price_level') if item.get('price_level') is not None else '정보 없음'}"
        )

    return "\n".join(lines) + "\n"


def _to_ui_place(restaurant, index):
    raw = restaurant.get("price_level")
    price_level = _safe_int(raw) if raw not in (None, 0) else None
    if price_level is not None:
        price_level = min(4, max(1, price_level))

    return {
        "id": f"api-{index}",
        "name": restaurant.get("name", "이름 없음"),
        "category": restaurant.get("category", "음식점"),
        "rating": float(restaurant.get("rating", 0) or 0),
        "user_ratings_total": int(restaurant.get("review_count", 0) or 0),
        "price_level": price_level,
        "formatted_address": restaurant.get("address", "주소 정보 없음"),
        "distance_m": _distance_to_ui_number(restaurant.get("distance")),
        "reviews": restaurant.get("reviews") or [
            restaurant.get("recommend_reason", "조건에 맞는 추천 후보입니다."),
        ],
        "tags": _build_tags(restaurant),
        "hue": 40 + (index * 55) % 260,
        "recommend_reason": restaurant.get("recommend_reason", ""),
    }


def _build_tags(restaurant):
    tags = []

    if restaurant.get("category"):
        tags.append(restaurant["category"])
    if _safe_float(restaurant.get("rating")) >= 4:
        tags.append("평점 높음")
    if (
        restaurant.get("price_level") not in (None, 0)
        and _safe_int(restaurant.get("price_level")) <= 2
    ):
        tags.append("부담 적음")

    return tags[:3] or ["추천"]


def _distance_to_ui_number(distance):
    try:
        return int(distance)
    except (TypeError, ValueError):
        return 0


def _safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _rating_condition_label(state):
    symbols = {"gte": ">=", "lte": "<=", "gt": ">", "lt": "<"}
    conditions = state.get("rating_conditions") or []
    return " and ".join(
        f"rating {symbols.get(item.get('operator'), '?')} {item.get('value')}"
        for item in conditions
    ) or "제한 없음"


app.mount("/", StaticFiles(directory=DESIGN_DIR, html=True), name="design")
