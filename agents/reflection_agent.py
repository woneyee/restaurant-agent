import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from tools.rating_filter import rating_matches

load_dotenv()


class ReflectionAgent:
    """
    LLM이 추천 결과를 스스로 검토하고 재시도 여부를 판단합니다.
    단순 조건문 대신 LLM이 품질을 평가해 더 유연한 판단을 합니다.
    """

    def __init__(self):
        api_key = os.getenv("GPT_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

    def reflect(self, recommendations: list, state: dict) -> dict:
        print("\n" + "=" * 50)
        print("Reflection Agent: LLM이 추천 결과를 검토합니다")
        print("=" * 50)

        rec_lines = [
            f"  - {r.get('name')}: 별점 {r.get('rating')}, "
            f"리뷰 {r.get('review_count')}개, 가격레벨 {r.get('price_level')}, "
            f"분위기 {r.get('is_good_atmosphere', False)}"
            for r in recommendations
        ]
        rec_text = "\n".join(rec_lines) if rec_lines else "  (결과 없음)"

        prompt = f"""맛집 추천 결과를 검토하고 재시도 여부를 판단하세요.

사용자 요청 조건:
- 위치: {state.get('location')}
- 별점 조건: {state.get('rating_conditions') or '없음'}
- 최대 가격대: {state.get('max_price') or '제한 없음'} (1=저가~4=고가)
- 분위기 필요: {state.get('need_atmosphere')}
- 요청 개수: 3개

추천 결과 ({len(recommendations)}개):
{rec_text}

판단 기준:
- 결과가 0개 → need_retry: true (필수)
- 결과가 2개 미만 → need_retry: true
- 결과가 3개 이상이고 조건을 어느 정도 충족 → need_retry: false
- 가격 조건이 있는데 price_level이 조건 초과 → need_retry: true 고려
- 결과의 rating이 사용자의 별점 조건을 충족하지 않음 → need_retry: true

다음 JSON 형식으로만 답하세요:
{{"need_retry": true 또는 false, "reason": "판단 이유 한 문장"}}"""

        print(f"\nReflection:\n추천 {len(recommendations)}개 결과를 LLM이 검토합니다.")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "맛집 추천 품질을 검토하는 에이전트입니다. JSON으로만 응답하세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
            )
            result = json.loads(response.choices[0].message.content)

        except Exception as error:
            # LLM 실패 시 규칙 기반 fallback
            print(f"⚠️ LLM 평가 실패 ({error}), 규칙 기반으로 대체합니다.")
            need_retry = len(recommendations) < 2
            result = {
                "need_retry": need_retry,
                "reason": "결과 부족" if need_retry else "추천 결과가 충분합니다.",
            }

        violations = _find_condition_violations(recommendations, state)
        if violations:
            result = {
                "need_retry": True,
                "reason": "조건 불충족: " + ", ".join(violations),
            }

        print(f"\nReflection Observation:")
        print(f"  need_retry: {result.get('need_retry')}")
        print(f"  reason: {result.get('reason')}")
        print("=" * 50 + "\n")

        return result


def _find_condition_violations(recommendations, state):
    violations = []
    if len(recommendations) < 2:
        violations.append("추천 결과 부족")

    rating_conditions = state.get("rating_conditions") or []
    if rating_conditions and any(
        not rating_matches(item.get("rating"), rating_conditions)
        for item in recommendations
    ):
        violations.append("별점 조건")

    max_price = state.get("max_price")
    if max_price is not None and any(
        item.get("price_level") in (None, 0)
        or int(item["price_level"]) > int(max_price)
        for item in recommendations
    ):
        violations.append("가격 조건 또는 가격 정보 없음")

    if state.get("need_atmosphere") and any(
        not item.get("is_good_atmosphere")
        for item in recommendations
    ):
        violations.append("분위기 조건")

    category = state.get("category")
    if category and any(item.get("category") != category for item in recommendations):
        violations.append("음식 종류 조건")

    return violations
