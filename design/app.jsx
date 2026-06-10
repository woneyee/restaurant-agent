/* global React, ReactDOM, window */

const { useState, useRef, useEffect, useCallback } = React;
const { Mascot, MascotBig, Squiggle, ResultsGrid, runAgents } = window;
const { TweaksPanel, useTweaks, TweakSection, TweakRadio, TweakSlider, TweakToggle, TweakButton, TweakColor } = window;

// ─────────────────────────────────────────────
// Chat message types streamed by the agent
//   { type: "user", text }
//   { type: "bot",  text }
//   { type: "planner", state }
//   { type: "react", step, thought, action, observation? }
//   { type: "reflect", text }
//   { type: "fallback", from, to }
// ─────────────────────────────────────────────

function UserBubble({ text }) {
  return (
    <div className="bubble user">
      <div className="who">나</div>
      {text}
    </div>
  );
}

function BotBubble({ text, faint }) {
  return (
    <div className={`bubble bot ${faint ? "faint" : ""}`}>
      <div className="who">eato</div>
      {text}
    </div>
  );
}

function PlannerCard({ state }) {
  const priceLabel = state.max_price === 1 ? "가성비 (₩)"
                    : state.max_price === 2 ? "적당 (₩₩)"
                    : state.max_price != null ? "프리미엄 (₩₩₩)" : "제한 없음";
  return (
    <div className="state-card">
      <div className="head">
        <span className="tag">PLANNER</span>
        자연어 → 검색 조건 추출
      </div>
      <div className="state-grid">
        <div className="item"><div className="k">위치</div><div className="v">{state.location || "—"}</div></div>
        <div className="item"><div className="k">음식 종류</div><div className="v">{state.category ? <span className="chip">{state.category}</span> : "any"}</div></div>
        <div className="item"><div className="k">별점 조건</div><div className="v">{
          state.rating_conditions?.length
            ? state.rating_conditions.map(c => `${c.value}점 ${c.operator === "gte" ? "이상" : c.operator === "lte" ? "이하" : c.operator === "gt" ? "초과" : "미만"}`).join(", ")
            : "제한 없음"
        }</div></div>
        <div className="item"><div className="k">가격대</div><div className="v">{priceLabel}</div></div>
        <div className="item"><div className="k">목적</div><div className="v">{state.purpose || "—"}</div></div>
        <div className="item" style={{ gridColumn: "1 / -1" }}>
          <div className="k">분위기 필요?</div>
          <div className="v">{state.need_atmosphere ? "🌿 예 — 리뷰 분석 필요" : "아니요"}</div>
        </div>
      </div>
    </div>
  );
}

function ReflectFlag({ text }) {
  return (
    <div className="flag reflect">
      <span className="emoji">🪞</span>
      <div><b>Reflection</b> — {text}</div>
    </div>
  );
}

function FallbackFlag({ from, to }) {
  return (
    <div className="flag fallback">
      <span className="emoji">🛟</span>
      <div>
        <b>Fallback</b> — 조건을 자동 완화할게요.<br />
        <span style={{ fontSize: 12.5, opacity: 0.8 }}>
          rating <code>{from.rating}</code> → <code>{to.rating}</code> ·
          {" "}price <code>{from.price}</code> → <code>{to.price}</code>
        </span>
      </div>
    </div>
  );
}

// ─── main App ────────────────────────────────────────────────

const EXAMPLES = [
  "전주 객사에서 분위기 좋은 한식 맛집 찾아줘",
  "전주 한옥마을에서 조용한 카페 찾아줘",
  "전북대에서 친구랑 가기 좋은 가성비 맛집 찾아줘",
];

function App() {
  // Tweaks ----------------------------------------------------
  const [t, setTweak] = useTweaks(/*EDITMODE-BEGIN*/{
    "theme": "mint",
    "speed": 1,
    "autoDemo": false
  }/*EDITMODE-END*/);

  useEffect(() => {
    document.body.setAttribute("data-theme", t.theme);
  }, [t.theme]);

  // Chat state ------------------------------------------------
  const [messages, setMessages] = useState([]);
  const [running, setRunning]   = useState(false);
  const [results, setResults]   = useState(null);     // final places
  const [resultsState, setResultsState] = useState(null);
  const [usedFallback, setUsedFallback] = useState(false);
  const [input, setInput] = useState("");

  const scrollerRef = useRef(null);
  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, running]);

  const submit = useCallback(async (text) => {
    if (running) return;
    const q = (text ?? input).trim();
    if (!q) return;

    setInput("");
    setRunning(true);
    setResults(null);
    setUsedFallback(false);
    setMessages(prev => [...prev, { type: "user", text: q }]);

    const emit = (e) => {
      setMessages(prev => {
        // react-observe attaches to a pending react step
        if (e.kind === "react-observe") {
          const idx = [...prev].reverse().findIndex(m => m.type === "react" && m.step === e.step && !m.observation);
          if (idx !== -1) {
            const real = prev.length - 1 - idx;
            const copy = prev.slice();
            copy[real] = { ...copy[real], observation: e.observation };
            return copy;
          }
        }
        if (e.kind === "bot")      return [...prev, { type: "bot", text: e.text }];
        // Detailed agent trace remains in submission_trace files, not in the chat UI.
        if (e.kind === "planner" || e.kind === "react" || e.kind === "reflect" || e.kind === "fallback") return prev;
        return prev;
      });

      if (e.kind === "done") {
        if (e.needMoreInfo) {
          setResults(null);
        } else {
          setResults(e.results);
        }
        setResultsState(e.state);
        setUsedFallback(e.usedFallback);
        setMessages(prev => [...prev, {
          type: "bot",
          text: e.needMoreInfo
            ? (e.message || "원하는 지역과 음식 종류를 함께 알려주세요.")
            : e.results.length
            ? `${e.results.length}곳을 찾았어요. 오른쪽에서 확인해 주세요.`
            : "흐엉.. 조건에 맞는 곳을 못 찾았어요. 다시 알려주실래요?",
        }]);
      }
    };

    try {
      await runAgents(q, emit, { speed: t.speed });
    } finally {
      setRunning(false);
    }
  }, [running, input, t.speed]);

  // Auto-demo toggle ------------------------------------------
  useEffect(() => {
    if (t.autoDemo && !running && messages.length === 0) {
      const id = setTimeout(() => submit(EXAMPLES[0]), 400);
      return () => clearTimeout(id);
    }
  }, [t.autoDemo, running, messages.length, submit]);

  // ----------------------------------------------------------

  const visibleMessages = messages.filter(m => {
    if (["planner", "react", "reflect", "fallback"].includes(m.type)) return false;
    return true;
  });

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Mascot size={32} mood="happy" /></div>
          <div>
            <div className="brand-name">eato</div>
            <div className="brand-sub">동네 맛집 골라주는 AI · multi-agent demo</div>
          </div>
        </div>
        <div className="chips">
          <span className="pill"><span className="dot"></span>Planner</span>
          <span className="pill"><span className="dot" style={{ background: "var(--peach-deep)", boxShadow: "0 0 0 3px var(--peach-soft)" }}></span>ReAct</span>
          <span className="pill"><span className="dot" style={{ background: "var(--lilac-deep)", boxShadow: "0 0 0 3px #f1ecff" }}></span>Reflection</span>
        </div>
      </header>

      <div className="main">
        {/* LEFT — chat */}
        <section className="chat">
          <div className="chat-head">
            <Mascot size={44} mood={running ? "thinking" : "happy"} />
            <div className="who">
              <b>eato</b>
              <span>안녕하세요! 어떤 곳 찾아드릴까요?</span>
            </div>
            <span className="status">
              {running ? (<><span className="dot"></span>생각하는 중</>)
                       : (<><span className="dot" style={{ background: "var(--ink-3)", animation: "none" }}></span>대기 중</>)}
            </span>
          </div>

          <div className="scroller" ref={scrollerRef}>
            {visibleMessages.length === 0 && (
              <BotBubble text={
                <>
                  안녕하세요! 저는 <b>eato</b>예요 🍙<br/>
                  자연어로 편하게 말해주세요. 예를 들어<br/>
                  <i style={{ color: "var(--ink-3)" }}>“전주 객사에서 분위기 좋은 한식 맛집 찾아줘”</i><br/>
                  같이요!
                </>
              } />
            )}

            {visibleMessages.map((m, i) => {
              if (m.type === "user")    return <UserBubble    key={i} text={m.text} />;
              if (m.type === "bot")     return <BotBubble     key={i} text={m.text} />;
              return null;
            })}

            {running && (
              <div className="bubble bot" style={{ alignSelf: "flex-start" }}>
                <span className="typing"><span></span><span></span><span></span></span>
              </div>
            )}
          </div>

          <div className="dock">
            {!running && messages.length === 0 && (
              <div className="examples">
                {EXAMPLES.map((e, i) => (
                  <button key={i} className="example" onClick={() => submit(e)}>{e}</button>
                ))}
              </div>
            )}
            <div className="composer">
              <textarea
                placeholder="원하는 음식과 분위기를 말해주세요.  (예: 전주 객사에서 분위기 좋은 한식 맛집)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                rows={2}
              />
              <button
                className="send"
                onClick={() => submit()}
                disabled={running || !input.trim()}
              >보내기</button>
            </div>
          </div>
        </section>

        {/* RIGHT — stage */}
        <section className="stage">
          {!results && !running && (
            <div className="stage-empty">
              <div className="big-mascot"><MascotBig /></div>
              <h1>
                원하는 음식과 분위기를 말하면<br/>
                <span style={{
                  background: "linear-gradient(180deg, transparent 60%, var(--mint) 60%, var(--mint) 92%, transparent 92%)",
                  padding: "0 6px",
                }}>딱 맞는 맛집</span>
                을 찾아드려요
              </h1>
              <Squiggle />
            </div>
          )}

          {running && !results && (
            <div className="stage-empty">
              <Mascot size={120} mood="thinking" />
              <h1 style={{ marginTop: 16 }}>맛집을 찾고 있어요</h1>
              <p>조건에 맞는 곳을 확인하는 중입니다.</p>
            </div>
          )}

          {results && results.length > 0 && (
            <>
              <div className="results-head">
                <div>
                  <h2>
                    <span className="accent">{resultsState?.location}</span> 근처<br/>
                    이런 곳 어때요?
                  </h2>
                  <div className="meta" style={{ marginTop: 6 }}>
                    총 <b>{results.length}곳</b> 추천 ·{" "}
                    {usedFallback
                      ? <>fallback 적용됨 (조건 살짝 완화) 🛟</>
                      : <>조건에 딱 맞아요 ✨</>}
                  </div>
                </div>
                <Mascot size={64} mood="happy" />
              </div>
              <ResultsGrid places={results} />
            </>
          )}

          {results && results.length === 0 && (
            <div className="stage-empty">
              <Mascot size={120} mood="sleepy" />
              <h1>흐엉.. 못 찾았어요</h1>
              <p>조건을 살짝 바꿔서 다시 말해주실래요?</p>
            </div>
          )}
        </section>
      </div>

      {/* Tweaks panel */}
      <TweaksPanel title="Tweaks">
        <TweakSection label="테마 컬러" />
        <TweakRadio
          label="액센트"
          value={t.theme}
          onChange={v => setTweak("theme", v)}
          options={[
            { value: "mint",   label: "민트" },
            { value: "peach",  label: "피치" },
            { value: "lilac",  label: "라일락" },
            { value: "butter", label: "버터" },
          ]}
        />

        <TweakSection label="에이전트 진행 속도" />
        <TweakSlider
          label="속도"
          min={0.5} max={4} step={0.25}
          unit="×"
          value={t.speed}
          onChange={v => setTweak("speed", v)}
        />

        <TweakSection label="표시" />
        <TweakToggle
          label="첫 실행에 데모 자동 시작"
          value={t.autoDemo}
          onChange={v => setTweak("autoDemo", v)}
        />

        <TweakSection label="대화 초기화" />
        <TweakButton
          label="대화 모두 지우기"
          onClick={() => {
            setMessages([]); setResults(null); setUsedFallback(false);
          }}
        />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
