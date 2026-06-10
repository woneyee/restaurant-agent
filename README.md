# 맛집 추천 AI Agent

Agentic Design Pattern을 활용한 맛집 탐색 및 추천 시스템입니다.  
사용자의 자연어 입력(지역, 음식 종류, 가격대, 분위기)을 분석하고, 여러 패턴을 조합해 최적의 맛집을 추천합니다.

---

## 적용한 Agentic Design Pattern

| 패턴 | 파일 | 설명 |
|------|------|------|
| **ReAct** (필수) | `agents/react_agent.py` | Thought → Action → Observation → Final Answer 반복 루프. 8단계 도구 호출 후 최종 추천 생성 |
| **Plan-and-Solve** | `agents/planner.py` | 사용자 자연어를 location / category / max_price / need_atmosphere 등 구조화된 state로 분해 |
| **Reflection** | `agents/reflection_agent.py` | 추천 결과 개수·조건 충족 여부를 자체 검토 후 부족하면 fallback 재시도 결정 |
| **Tool Use** | `tools/` | 맛집 검색·별점 필터·리뷰 수 필터·가격 필터·거리 정렬·분위기 분석 도구를 Agent가 직접 호출 |
| **Memory** | `memory/user_memory.py` | 방문 이력·선호 카테고리·가격대를 JSON 파일에 저장하고 추천 가중치에 반영 |

> LangGraph `StateGraph`로 위 패턴들을 **Supervisor 흐름**으로 연결합니다.  
> `planner → (ask_user) → react → reflection → (fallback) → final`

---

## 프로젝트 구조

```
restaurant-agent/
├── main.py                  # CLI 진입점 (LangGraph 실행)
├── api.py                   # FastAPI 서버 (웹 UI용)
├── requirements.txt
├── .env                     # API 키 설정
│
├── agents/
│   ├── graph_agent.py       # LangGraph Supervisor 정의
│   ├── planner.py           # Plan-and-Solve: 요청 파싱
│   ├── react_agent.py       # ReAct: 도구 호출 루프
│   └── reflection_agent.py  # Reflection: 결과 검토
│
├── tools/
│   ├── restaurant_search.py # Google Places API / 샘플 데이터 검색
│   ├── rating_filter.py     # 별점·리뷰 수·가격 필터
│   ├── distance_tool.py     # 거리 기준 정렬
│   └── review_analysis.py   # 리뷰 키워드 기반 분위기 분석
│
├── memory/
│   └── user_memory.py       # 사용자 선호도 저장 및 가중치 계산
│
└── data/
    └── restaurants.json     # 샘플 맛집 데이터 (25개, 전주 객사/한옥마을/전북대)
```

---

## 실행 환경

### 요구 사항

- **Python**: 3.12 이상
- **운영체제**: Windows / macOS / Linux

### 패키지 설치

```bash
# 가상환경 생성 (권장)
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# 패키지 설치
pip install -r requirements.txt
```

### API 키 설정 (선택)

`.env` 파일에 API 키를 입력합니다. **키가 없어도 샘플 데이터로 동작**합니다.

```env
GOOGLE_API_KEY=your_google_places_api_key_here
```

| API | 용도 | 없을 때 |
|-----|------|---------|
| Google Places Text Search | 실시간 맛집 검색 | `data/restaurants.json` 샘플 데이터 자동 사용 |

---

## 실행 방법

### CLI (터미널)

```bash
python main.py
```

실행 후 프롬프트에 자연어로 입력:

```
💬 User Input: 전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.
```

### FastAPI 웹 서버

```bash
uvicorn api:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속 또는 API 직접 호출:

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "전주 객사 근처 한식 맛집 추천해줘"}'
```

API 요청을 실행할 때마다 실제 Planner/ReAct/Reflection 실행 기록이
`logs/submission_trace.json`과 `logs/submission_trace.md`에 저장됩니다.
두 파일에는 실제 도구 호출 순서, 도구 입력값, Observation, fallback 전후 조건,
최종 추천 결과가 포함됩니다. Markdown 파일은 제출 문서에 바로 첨부할 수 있습니다.

---

## 예외 처리 목록

| 상황 | 처리 방식 |
|------|-----------|
| 존재하지 않는 지역 입력 | 지원 지역 안내 후 빈 결과 반환 → Reflection이 감지하여 fallback |
| 검색 결과 없음 | Reflection Agent가 조건 완화(가격·분위기 제거) 후 재시도 |
| 음식 종류 모호 | Planner가 모호성 감지 → 카테고리 없이 위치 기반 검색으로 대체 |
| API 호출 실패 | `data/restaurants.json` 샘플 데이터로 자동 대체 |
| 사용자 조건 부족 | Planner가 누락 필드 감지 → `ask_user` 노드에서 추가 입력 요청 |

---

## 테스트 시나리오

### 입력 프롬프트

```
전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘.
너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.
```

### 예상 실행 흐름 (Trace)

```
[LangGraph] planner 노드
  Thought: 자연어 요청 파싱
  Action:  Rule-based NLP 실행
  → location: "전주 객사", max_price: 2, need_atmosphere: True

[LangGraph] react 노드
  Thought 1: 위치 기반 검색 필요
  Action 1: restaurant_search(location="전주 객사")
  Observation 1: 6개 맛집 발견

  Thought 2: 리뷰 수 기반 신뢰도 필터
  Action 2: filter_by_review_count(min_reviews=50)
  Observation 2: 6개 → 6개

  Thought 3: 별점 필터
  Action 3: filter_by_rating(min_rating=4.0)
  Observation 3: 6개 → 5개

  Thought 4: 가격 필터 (max_price=2)
  Action 4: filter_by_price(max_price=2)
  Observation 4: 5개 → 3개

  Thought 5: 분위기 리뷰 키워드 분석
  Action 5: filter_by_atmosphere()
  Observation 5: 3개 → 2개

  Thought 6: 메모리 가중치 적용
  Action 6: apply_memory_weights()
  Observation 6: 2개 재정렬

  Thought 7: 거리 기준 정렬
  Action 7: sort_by_distance()
  Observation 7: 2개 정렬

  Thought 8: 상위 3개 선택
  Action 8: select_top_k(k=3)
  Observation 8: 2개 최종 후보

  Final Answer: 추천 결과 출력

[LangGraph] reflection 노드
  → 결과 2개 (< 3) → need_retry: True

[LangGraph] fallback 노드
  → max_price=None, need_atmosphere=False 완화 후 재시도

[LangGraph] final 노드
  → 최종 3곳 추천 완료
```

### 최종 추천 예시 출력

```
1. 🍽️ 전주 비빔밥 전문점 '전주집'
   📍 주소: 전주 객사 근처
   🏷️  카테고리: 한식
   ⭐ 별점: 4.8/5.0 (342개 리뷰)
   💰 가격대: $$
   📏 거리: 120m
   ✨ 추천 이유: ✓ 높은 별점 (4.8점) / ✓ 리뷰 다수 (342개) / ...

2. 🍽️ 객사 술집 '한잔'
   ...

3. 🍽️ 객사 돈까스 '도톤보리'
   ...
```

---

## 지원 데이터

샘플 데이터는 `data/restaurants.json`에 포함되어 있습니다 (총 25개).

| 지역 | 포함 카테고리 |
|------|--------------|
| 전주 객사 | 한식, 일식, 양식, 술집 |
| 전주 한옥마을 | 한식, 카페, 디저트, 술집 |
| 전북대 | 한식, 일식, 카페 |
