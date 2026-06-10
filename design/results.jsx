/* global React, window */

// ─────────────────────────────────────────────
// Restaurant result card + grid
// ─────────────────────────────────────────────

function Stars({ rating }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  const s = "★".repeat(full) + (half ? "☆" : "");
  return <span className="stars">{s.padEnd(5, "·")}</span>;
}

function priceLabel(level) {
  if (level == null) return "가격 정보 없음";
  return "₩".repeat(level) + "·".repeat(Math.max(0, 4 - level));
}

function DoodlePhoto({ hue, kind = "bowl" }) {
  // soft tinted background + simple SVG food doodle
  const bg = `oklch(0.93 0.06 ${hue})`;
  const ink = "#3d3a35";

  let doodle;
  if (kind === "bowl") {
    doodle = (
      <g>
        {/* table */}
        <line x1="20" y1="92" x2="240" y2="92" stroke={ink} strokeWidth="1.4" />
        {/* bowl */}
        <path d="M 80 70 Q 130 110 180 70 L 178 76 Q 130 116 82 76 Z" fill="#fff" stroke={ink} strokeWidth="2" strokeLinejoin="round" />
        {/* rice + toppings */}
        <ellipse cx="130" cy="68" rx="46" ry="8" fill="#fff" stroke={ink} strokeWidth="2" />
        <circle cx="118" cy="64" r="4" fill={`oklch(0.7 0.15 ${hue + 30})`} stroke={ink} strokeWidth="1.4" />
        <circle cx="138" cy="62" r="3" fill={`oklch(0.75 0.12 ${hue - 40})`} stroke={ink} strokeWidth="1.4" />
        <path d="M 124 60 q 6 -6 12 0" stroke={ink} strokeWidth="1.4" fill="none" />
        {/* steam */}
        <path d="M 120 50 q 2 -6 -2 -10" stroke={ink} strokeWidth="1.4" fill="none" strokeLinecap="round" />
        <path d="M 132 48 q 2 -8 -2 -12" stroke={ink} strokeWidth="1.4" fill="none" strokeLinecap="round" />
        <path d="M 144 50 q 2 -6 -2 -10" stroke={ink} strokeWidth="1.4" fill="none" strokeLinecap="round" />
      </g>
    );
  }

  return (
    <div className="r-photo" style={{
      background: `linear-gradient(135deg, ${bg}, oklch(0.96 0.04 ${hue+30}))`,
    }}>
      <svg className="doodle" viewBox="0 0 260 120" preserveAspectRatio="xMidYMid slice">
        {doodle}
      </svg>
      <span className="ph-label">photo placeholder</span>
    </div>
  );
}

function ResultCard({ place, rank }) {
  const rankClass = rank === 1 ? "gold" : rank === 2 ? "silver" : rank === 3 ? "bronze" : "";
  const quote = place.reviews[0];

  return (
    <article className="r-card">
      <div className={`rank ${rankClass}`}>#{rank}</div>
      <DoodlePhoto hue={place.hue} />
      <div className="r-body">
        <div className="r-name">
          {place.name}
          <span className="cat">{place.category}</span>
        </div>
        <div className="r-meta">
          <Stars rating={place.rating} />
          <b>{place.rating.toFixed(1)}</b>
          <span className="muted">· 리뷰 {place.user_ratings_total.toLocaleString()}</span>
          <span className="spacer" />
          <span className="muted">{priceLabel(place.price_level)}</span>
        </div>
        <div className="r-addr">📍 {place.formatted_address} · {place.distance_m}m</div>
        <div className="r-quote">{quote}</div>
        <div className="r-tags">
          {place.tags.map((t, i) => (
            <span key={i} className={`r-tag ${i === 0 ? "atmo" : ""}`}>#{t}</span>
          ))}
        </div>
        <div className="r-actions">
          <button className="btn">길찾기</button>
          <button className="btn">전화</button>
          <button className="btn primary">예약</button>
        </div>
      </div>
    </article>
  );
}

function ResultsGrid({ places }) {
  return (
    <div className="results-grid">
      {places.map((p, i) => <ResultCard key={p.id} place={p} rank={i + 1} />)}
    </div>
  );
}

Object.assign(window, { ResultsGrid, ResultCard });
