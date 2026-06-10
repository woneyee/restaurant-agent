import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """당신은 맛집 추천 AI의 요청 분석 에이전트입니다.
사용자의 자연어 요청을 분석해서 다음 JSON 형식으로 정확히 추출하세요.

반환 형식 (JSON만 반환):
{
  "location": "지역명 문자열. 예: '전주 객사', '전주 한옥마을', '전북대'. 언급 없으면 null",
  "category": "음식 종류. 예: '한식', '일식', '양식', '카페', '디저트', '술집'. 없으면 null",
  "rating_conditions": "별점 조건 목록. 예: '4.5점 이상'=[{\"operator\":\"gte\",\"value\":4.5}], 언급 없으면 []",
  "max_price": "가격대 정수. '저렴/가성비/비싸지않게'=2, '고급/프리미엄'=4, 언급 없으면 null",
  "need_atmosphere": "분위기가 중요한지 boolean. '친구', '데이트', '분위기', '감성', '모임' 포함시 true",
  "purpose": "'친구', '데이트', '가족', '혼밥', '비즈니스', '일반' 중 하나",
  "is_ambiguous": "위치 또는 핵심 조건이 불명확하면 true, 아니면 false",
  "clarification_questions": ["추가로 물어봐야 할 질문 목록. 명확하면 빈 배열 []"]
}"""


class PlannerAgent:
    """LLM이 사용자 자연어 요청을 구조화된 state로 변환합니다."""

    def __init__(self):
        api_key = os.getenv("GPT_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

    def plan(self, user_input: str) -> dict:
        user_input = user_input.strip().lstrip("﻿")

        print("\n" + "=" * 60)
        print("Planner Agent: 사용자 요청 분석 시작 (LLM)")
        print("=" * 60)
        print(f"📝 입력: {user_input}")
        print("\n[Thought] 자연어 요청에서 구조화된 정보를 LLM으로 추출합니다")
        print("[Action] GPT-4o-mini 호출 중...")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=300,
            )
            state = json.loads(response.choices[0].message.content)

        except Exception as error:
            print(f"\n⚠️ LLM 파싱 실패: {error}. 기본값으로 대체합니다.")
            state = {
                "location": None,
                "category": None,
                "rating_conditions": [],
                "max_price": None,
                "need_atmosphere": False,
                "purpose": "일반",
                "is_ambiguous": True,
                "clarification_questions": ["원하는 지역과 음식 종류를 알려주세요."],
            }

        state["rating_conditions"] = _extract_rating_conditions(user_input)
        state = _apply_explicit_request_rules(user_input, state)
        state["raw_input"] = user_input

        print("\n[Observation] LLM 파싱 완료")
        print("📊 추출된 상태:")
        print(f"   - 위치: {state.get('location') or '❓ 미명시'}")
        print(f"   - 음식: {state.get('category') or '❓ 미명시'}")
        print(f"   - 별점 조건: {state.get('rating_conditions') or '없음'}")
        print(f"   - 가격: {_price_label(state.get('max_price'))}")
        print(f"   - 분위기 필요: {state.get('need_atmosphere')}")
        print(f"   - 목적: {state.get('purpose')}")

        if state.get("is_ambiguous"):
            print("\n⚠️ 모호한 입력 감지:")
            for q in state.get("clarification_questions", []):
                print(f"   - {q}")

        print("=" * 60 + "\n")
        return state


def _price_label(level):
    return {1: "💰 저가 ($)", 2: "💰 중가 ($$)", 3: "💰 고가 ($$$)", 4: "💰 최고가 ($$$$)"}.get(level, "💰 무제한")


def _extract_rating_conditions(user_input: str) -> list:
    """요청에 명시된 별점 숫자와 비교 연산자를 그대로 추출합니다."""
    pattern = re.compile(
        r"(?:별점|평점)?\s*([0-5](?:\.\d+)?)\s*점?\s*"
        r"(이상|이하|초과|미만|넘는|넘게|보다\s*높(?:은|게)?|보다\s*낮(?:은|게)?)"
    )
    operator_map = {
        "이상": "gte",
        "이하": "lte",
        "초과": "gt",
        "미만": "lt",
        "넘는": "gt",
        "넘게": "gt",
    }
    conditions = []
    for value, phrase in pattern.findall(user_input):
        normalized_phrase = re.sub(r"\s+", " ", phrase).strip()
        operator = operator_map.get(normalized_phrase)
        if operator is None:
            operator = "gt" if "높" in normalized_phrase else "lt"
        conditions.append({"operator": operator, "value": float(value)})
    return conditions


def _apply_explicit_request_rules(user_input: str, state: dict) -> dict:
    """LLM이 놓치기 쉬운 명시 조건만 결정적으로 보정합니다."""
    text = user_input.replace(" ", "")
    updated = dict(state)

    category_keywords = {
        "카페": ("카페", "커피", "커피숍"),
        "디저트": ("디저트", "베이커리", "빵집"),
        "한식": ("한식", "백반", "비빔밥", "한정식"),
        "일식": ("일식", "초밥", "스시", "라멘", "우동"),
        "양식": ("양식", "파스타", "스테이크", "이탈리안"),
        "중식": ("중식", "짜장", "짬뽕", "탕수육"),
        "술집": ("술집", "주점", "바", "펍"),
    }
    for category, keywords in category_keywords.items():
        if any(keyword in text for keyword in keywords):
            updated["category"] = category
            break

    if any(word in text for word in ("너무비싸지않", "비싸지않", "가성비", "저렴", "싼곳")):
        updated["max_price"] = 2
    if any(word in text for word in ("친구", "데이트", "분위기", "감성", "모임", "조용")):
        updated["need_atmosphere"] = True
    if "친구" in text:
        updated["purpose"] = "친구"

    return updated
