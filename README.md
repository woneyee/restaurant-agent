# Restaurant Agent

이 프로젝트는 오픈소스소프트웨어개발의 일환이며,
OpenAI와 Google Maps Platform을 활용한 동네 맛집 추천 Multi-Agent 웹앱입니다.

사용자의 자연어 요청에서 지역, 음식 종류, 별점, 가격대, 분위기 조건을 추출하고,
ReAct Agent가 검색·필터링·정렬 도구를 호출하여 최대 3곳을 추천합니다.

```text
전주 객사에서 친구랑 가기 좋은 너무 비싸지 않은 맛집 찾아줘
전북대 근처 별점 4.3 이상 카페 추천해줘
전주 한옥마을에서 평점 4.0 이하인 곳 찾아줘
```

## 주요 기능

- 지역과 음식 종류 기반 Google Places 검색
- `이상`, `이하`, `초과`, `미만` 별점 조건 적용
- 리뷰 수, 가격대, 분위기, 거리 기반 필터링 및 정렬
- 카페 요청 시 카페 장소 유형만 추천하는 카테고리 검증
- 추천 결과 조건 검토 및 결과 부족 시 fallback 재검색
- 외부 API 실패 시 로컬 샘플 데이터 사용
- 실제 Agent 실행 과정을 제출용 JSON·Markdown Trace로 저장
- 웹 UI에서는 상세 Trace를 숨기고 검색 상태와 최종 결과만 표시

## Agentic Design Pattern

| 패턴 | 구현 | 설명 |
|---|---|---|
| **ReAct** | `agents/react_agent.py` | LLM이 Thought → Action → Observation 루프를 수행하며 필요한 도구를 선택합니다. 호출 단계 수와 순서는 요청에 따라 달라집니다. |
| **Plan-and-Solve** | `agents/planner.py` | 자연어 요청을 `location`, `category`, `rating_conditions`, `max_price`, `need_atmosphere`, `purpose`로 구조화합니다. |
| **Reflection** | `agents/reflection_agent.py` | 추천 개수와 음식 종류·별점·가격·분위기 조건을 다시 검증합니다. |
| **Tool Use** | `tools/` | 맛집 검색, 리뷰 수·별점·가격 필터, 분위기 분석, 거리 정렬 도구를 호출합니다. |
| **Memory** | `memory/user_memory.py` | 저장된 선호 위치·카테고리를 읽어 추천 순위 가중치에 반영할 수 있습니다. 웹 추천 결과를 방문 기록으로 자동 저장하지는 않습니다. |

### 실행 흐름

웹 API의 실행 흐름:

```text
Planner → ReAct → Reflection → 필요 시 fallback ReAct → 최종 추천
```

CLI의 실행 흐름:

```text
LangGraph Supervisor
→ planner
→ 위치 누락 시 ask_user
→ react
→ reflection
→ 필요 시 fallback
→ final
```

fallback에서는 가격과 분위기 조건을 완화할 수 있지만, 사용자가 명시한 음식 종류와
별점 조건은 유지됩니다.

## 사용 도구

| 도구 | 파일 | 역할 |
|---|---|---|
| `search_restaurants` | `tools/restaurant_search.py` | 지역과 음식 종류로 맛집 후보 검색 |
| `filter_by_review_count` | `tools/rating_filter.py` | 최소 리뷰 수 이상 후보 선별 |
| `filter_by_rating` | `tools/rating_filter.py` | 사용자 별점 비교 조건 적용 |
| `filter_by_price` | `tools/rating_filter.py` | 최대 가격대 조건 적용 |
| `filter_by_atmosphere` | `tools/review_analysis.py` | 리뷰와 장소 메타데이터의 분위기 키워드 분석 |
| `sort_by_distance` | `tools/distance_tool.py` | 검색 지역에서 가까운 순서로 정렬 |

## 외부 API

### OpenAI API

`gpt-4o-mini`를 다음 작업에 사용합니다.

- Planner Agent의 자연어 요청 분석
- ReAct Agent의 도구 선택
- Reflection Agent의 추천 결과 검토

`GPT_API_KEY`가 없거나 OpenAI API 호출이 실패하면 일부 단계는 규칙 기반 fallback으로
전환됩니다. 다만 지역명과 복잡한 자연어 조건을 안정적으로 분석하여 전체 웹앱 기능을
사용하려면 `GPT_API_KEY` 설정을 권장합니다.

OpenAI API 키 생성: <https://platform.openai.com/api-keys>

### Google Maps Platform API

현재 구현은 다음 Google Maps Platform Web Service를 사용합니다.

| API | 용도 |
|---|---|
| **Places Text Search API (Legacy)** | 지역과 음식 종류를 조합하여 장소 후보 검색 |
| **Place Details API (Legacy)** | Place ID로 실제 리뷰 조회 |
| **Geocoding API** | 입력 지역을 위도·경도로 변환하여 장소까지의 직선거리 계산 |

현재 코드는 Google Places의 Legacy REST 엔드포인트를 사용합니다. Google Cloud 프로젝트에서
결제 계정을 연결하고 **Places API**와 **Geocoding API**를 활성화해야 합니다. 운영 환경에서는
API 제한과 서버 IP 제한을 설정하는 것이 좋습니다.

Google API 설정 문서:

- Places Text Search: <https://developers.google.com/maps/documentation/places/web-service/legacy/search-text>
- Place Details: <https://developers.google.com/maps/documentation/places/web-service/legacy/details>
- Geocoding API 키 설정: <https://developers.google.com/maps/documentation/geocoding/get-api-key>

`GOOGLE_API_KEY`가 없거나 Google API 호출에 실패하면 `data/restaurants.json`의 샘플
데이터를 사용합니다. 샘플 데이터는 전주 객사, 전주 한옥마을, 전북대만 지원합니다.

## 설치 및 API 키 설정

### 요구 사항

- Python 3.12 이상
- 인터넷 연결
  - OpenAI 및 Google API 사용 시 필요
  - 웹 UI의 React, Babel, Google Fonts CDN 로딩 시 필요

### 1. 저장소 복제

```bash
git clone https://github.com/woneyee/restaurant-agent.git
cd restaurant-agent
```

### 2. 가상환경 및 패키지 설치

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. `.env` 생성

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

생성한 `.env`에 키를 입력합니다.

```env
GOOGLE_API_KEY=your_google_api_key
GPT_API_KEY=your_openai_api_key
```

`.env`는 `.gitignore`에 포함되어 있으므로 Git에 커밋되지 않습니다. 실제 API 키를
`.env.example`, 소스 코드, README에 직접 작성하지 마세요.

## 웹앱 실행

가상환경을 활성화한 상태에서 실행합니다.

```bash
uvicorn api:app --reload --port 8000
```

Windows에서 프로젝트의 가상환경 실행 파일을 직접 사용하는 방법:

```powershell
.\.venv\Scripts\uvicorn.exe api:app --reload --port 8000
```

브라우저에서 다음 주소로 접속합니다.

```text
http://127.0.0.1:8000
```

웹 UI에는 상세 Thought/Action/Observation Trace가 표시되지 않습니다. 검색 중 상태와
최종 추천 결과만 보여줍니다.

### API 직접 호출

Windows PowerShell:

```powershell
$body = @{ query = "전북대 근처 카페 추천해줘" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/recommend" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

curl:

```bash
curl -X POST http://127.0.0.1:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"query":"전북대 근처 카페 추천해줘"}'
```

## CLI 실행

LangGraph Supervisor 흐름을 터미널에서 실행합니다.

```bash
python main.py
```

CLI에서 위치가 누락되면 지역과 음식 종류를 추가로 질문합니다.


## 테스트

### 시나리오 실행

```bash
python test_scenario.py
```

실행 프롬프트:

```text
전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘.
너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.
```


## 프로젝트 구조

```text
restaurant-agent/
├── api.py                     # FastAPI 웹 서버와 제출용 Trace 저장
├── main.py                    # LangGraph CLI 진입점
├── test_scenario.py           # 지정 시나리오 실행
├── .env.example               # API 키 환경 변수 예시
├── requirements.txt
├── agents/
│   ├── planner.py             # 자연어 요청 구조화
│   ├── react_agent.py         # ReAct 도구 호출 루프
│   ├── reflection_agent.py    # 추천 결과 조건 재검증
│   └── graph_agent.py         # CLI용 LangGraph Supervisor
├── tools/
│   ├── restaurant_search.py   # Google Places/Geocoding 및 샘플 검색
│   ├── rating_filter.py       # 리뷰 수·별점·가격 필터
│   ├── review_analysis.py     # Place Details 리뷰 기반 분위기 분석
│   └── distance_tool.py       # 거리 정렬
├── memory/
│   └── user_memory.py         # 사용자 선호 메모리
├── data/
│   └── restaurants.json       # Google API 실패 시 사용할 샘플 데이터
└── design/                    # 웹 UI 정적 파일
```
