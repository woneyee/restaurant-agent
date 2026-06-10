/* global window */

// ─────────────────────────────────────────────
// Frontend agent bridge.
// Calls the real Python Agent backend instead of mock JS data.
// Backend:
//   POST /api/recommend
//   Planner -> ReAct -> Tools -> Reflection -> Fallback
// ─────────────────────────────────────────────

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runAgents(query, emit, opts = {}) {
  const speed = opts.speed ?? 1;
  const wait = (ms) => delay(ms / speed);

  await wait(300);

  let payload;

  try {
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    payload = await response.json();
  } catch (error) {
    emit({
      kind: "bot",
      text: `백엔드 API 호출에 실패했어요. 서버가 실행 중인지 확인해주세요. (${error.message})`,
    });
    emit({
      kind: "done",
      state: {},
      results: [],
      usedFallback: false,
    });
    return;
  }

  const trace = payload.trace || [];

  for (const event of trace) {
    if (event.kind === "react" && event.observation) {
      emit({
        kind: "react",
        step: event.step,
        thought: event.thought,
        action: `${event.action}(${JSON.stringify(event.input || {})})`,
      });
      await wait(450);
      emit({
        kind: "react-observe",
        step: event.step,
        observation: event.observation,
      });
    } else {
      emit(event);
    }

    await wait(450);
  }

  if (payload.status === "need_more_info") {
    emit({
      kind: "done",
      state: payload.state || {},
      results: [],
      usedFallback: false,
      needMoreInfo: true,
      message: payload.message,
    });
    return;
  }

  emit({
    kind: "done",
    state: payload.state || {},
    results: payload.recommendations || [],
    usedFallback: Boolean(payload.used_fallback),
  });
}

Object.assign(window, { runAgents });
