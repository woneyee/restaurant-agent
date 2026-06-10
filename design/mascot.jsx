/* global React, window */

// ─────────────────────────────────────────────
// eato mascot — a soft rice-ball character
// SVG primitives only. Three sizes / moods.
// ─────────────────────────────────────────────

function Mascot({ size = 56, mood = "idle", wave = false }) {
  // mood: idle | thinking | happy | curious | sleepy
  const eye = (cx, cy) => {
    if (mood === "happy")    return <path d={`M ${cx-4} ${cy} q 4 -5 8 0`} stroke="#3d3a35" strokeWidth="2" fill="none" strokeLinecap="round" />;
    if (mood === "sleepy")   return <path d={`M ${cx-4} ${cy} q 4 4 8 0`} stroke="#3d3a35" strokeWidth="2" fill="none" strokeLinecap="round" />;
    if (mood === "thinking") return <circle cx={cx} cy={cy+1} r="2.2" fill="#3d3a35" />;
    return <ellipse cx={cx} cy={cy} rx="2.4" ry="3" fill="#3d3a35" />;
  };

  const cheek = (cx, cy) => <ellipse cx={cx} cy={cy} rx="4" ry="2.4" fill="#ffb3c1" opacity="0.7" />;

  const mouth = () => {
    if (mood === "happy")    return <path d="M 46 64 q 8 7 16 0" stroke="#3d3a35" strokeWidth="2.4" fill="none" strokeLinecap="round" />;
    if (mood === "thinking") return <path d="M 50 64 q 4 -2 8 0"  stroke="#3d3a35" strokeWidth="2.4" fill="none" strokeLinecap="round" />;
    if (mood === "sleepy")   return <path d="M 50 65 q 4 1 8 0"  stroke="#3d3a35" strokeWidth="2.4" fill="none" strokeLinecap="round" />;
    return <path d="M 48 63 q 6 4 12 0" stroke="#3d3a35" strokeWidth="2.4" fill="none" strokeLinecap="round" />;
  };

  return (
    <svg width={size} height={size} viewBox="0 0 108 108" className={wave ? "mascot-wave" : ""}>
      <defs>
        <radialGradient id="m-body" cx="40%" cy="38%" r="70%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#f6efe0" />
        </radialGradient>
      </defs>

      {/* shadow */}
      <ellipse cx="54" cy="100" rx="26" ry="4" fill="#3d3a35" opacity="0.12" />

      {/* rice-ball body (triangle with rounded corners) */}
      <path
        d="M 54 18
           C 64 18 70 30 84 56
           C 92 72 88 86 76 90
           C 66 93 42 93 32 90
           C 20 86 16 72 24 56
           C 38 30 44 18 54 18 Z"
        fill="url(#m-body)"
        stroke="#3d3a35"
        strokeWidth="2.4"
      />

      {/* nori (seaweed) wrap at bottom */}
      <path
        d="M 22 70
           C 30 78 78 78 86 70
           L 84 86
           C 80 92 28 92 24 86 Z"
        fill="#3d3a35"
      />
      <path
        d="M 22 70
           C 30 78 78 78 86 70"
        stroke="#3d3a35"
        strokeWidth="2"
        fill="none"
      />

      {/* face */}
      {eye(44, 58)}
      {eye(64, 58)}
      {cheek(40, 65)}
      {cheek(68, 65)}
      {mouth()}

      {/* sparkle */}
      <g opacity="0.9">
        <circle cx="86" cy="32" r="2" fill="#ffe07a" />
        <circle cx="80" cy="26" r="1.2" fill="#ffe07a" />
      </g>

      {/* tiny leaf hat */}
      <path d="M 54 16 q 6 -8 14 -2 q -2 8 -10 8 q -4 0 -4 -6 Z" fill="#9fdcc0" stroke="#3d3a35" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M 60 12 q 0 4 2 6" stroke="#3d3a35" strokeWidth="1.2" fill="none" />
    </svg>
  );
}

function MascotBig() {
  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <Mascot size={160} mood="happy" />
      {/* sparkles */}
      <svg width="40" height="40" viewBox="0 0 40 40" style={{ position: "absolute", top: -6, right: -10 }}>
        <path d="M 20 4 L 22 18 L 36 20 L 22 22 L 20 36 L 18 22 L 4 20 L 18 18 Z" fill="#ffe07a" stroke="#3d3a35" strokeWidth="1.4" strokeLinejoin="round" />
      </svg>
      <svg width="22" height="22" viewBox="0 0 22 22" style={{ position: "absolute", bottom: 12, left: -22 }}>
        <path d="M 11 2 L 12.5 9.5 L 20 11 L 12.5 12.5 L 11 20 L 9.5 12.5 L 2 11 L 9.5 9.5 Z" fill="#ffc9a8" stroke="#3d3a35" strokeWidth="1.2" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function Squiggle() {
  return (
    <svg width="220" height="20" viewBox="0 0 220 20" className="squiggle">
      <path d="M 4 12 Q 18 -2 32 12 T 60 12 T 88 12 T 116 12 T 144 12 T 172 12 T 200 12 T 216 12" stroke="#3d3a35" strokeWidth="2.2" fill="none" strokeLinecap="round" />
    </svg>
  );
}

Object.assign(window, { Mascot, MascotBig, Squiggle });
