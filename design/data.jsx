/* global window */

// ─────────────────────────────────────────────
// Mock data — fictional Jeonju-area restaurants
// Not a recreation of any specific listing.
// ─────────────────────────────────────────────

const PLACES = [
  {
    id: "p1",
    name: "객사뜰 한정식",
    category: "한식",
    rating: 4.6,
    user_ratings_total: 1284,
    price_level: 2,
    formatted_address: "전북 전주시 완산구 객사길 12",
    distance_m: 180,
    reviews: [
      "한지로 꾸민 인테리어가 정말 아늑해요. 분위기 좋아요.",
      "친구랑 오기 좋고 사진 찍기도 예뻐요.",
      "정갈한 반찬에 가격은 1인 2만원대.",
    ],
    tags: ["한정식", "정갈한 반찬", "한옥 분위기"],
    hue: 145,
  },
  {
    id: "p2",
    name: "달빛 비빔밥",
    category: "한식",
    rating: 4.4,
    user_ratings_total: 932,
    price_level: 1,
    formatted_address: "전북 전주시 완산구 풍남문2길 7",
    distance_m: 260,
    reviews: [
      "비빔밥 그릇이 깜찍하고 맛도 좋아요.",
      "혼밥하기에도 편안한 자리.",
      "양도 많고 가격도 합리적.",
    ],
    tags: ["비빔밥", "혼밥 OK", "가성비"],
    hue: 35,
  },
  {
    id: "p3",
    name: "한옥마루 가정식",
    category: "한식",
    rating: 4.5,
    user_ratings_total: 1567,
    price_level: 2,
    formatted_address: "전북 전주시 완산구 태조로 21",
    distance_m: 320,
    reviews: [
      "조용히 데이트하기 좋아요.",
      "마당 자리가 감성 가득.",
      "사장님이 친절하시고 음식 정성스러워요.",
    ],
    tags: ["조용한 분위기", "데이트", "감성"],
    hue: 280,
  },
  {
    id: "p4",
    name: "객사길 백반",
    category: "한식",
    rating: 4.2,
    user_ratings_total: 612,
    price_level: 1,
    formatted_address: "전북 전주시 완산구 객사3길 5",
    distance_m: 90,
    reviews: [
      "어머니 손맛 그대로.",
      "혼자 가도 편한 동네 백반집.",
      "메뉴 단순하고 빨라요.",
    ],
    tags: ["백반", "빠른 식사", "동네 맛집"],
    hue: 20,
  },
  {
    id: "p5",
    name: "풍남 솥밥",
    category: "한식",
    rating: 4.7,
    user_ratings_total: 884,
    price_level: 3,
    formatted_address: "전북 전주시 완산구 은행로 14",
    distance_m: 410,
    reviews: [
      "솥밥에서 김 올라올 때 분위기 최고.",
      "친구 데려갔는데 인테리어 너무 예쁘다고.",
      "가격대는 1인 3만원선.",
    ],
    tags: ["솥밥", "프리미엄", "인테리어 예쁨"],
    hue: 195,
  },
  {
    id: "p6",
    name: "전주 한지방",
    category: "한식",
    rating: 4.3,
    user_ratings_total: 743,
    price_level: 2,
    formatted_address: "전북 전주시 완산구 오목대길 9",
    distance_m: 380,
    reviews: [
      "한지 등이 따뜻하게 켜져서 분위기 좋아요.",
      "친구 모임으로 적당.",
      "반찬 종류가 많아서 좋음.",
    ],
    tags: ["한지 인테리어", "친구모임", "다양한 반찬"],
    hue: 55,
  },
  {
    id: "p7",
    name: "옥토끼 두부집",
    category: "한식",
    rating: 4.1,
    user_ratings_total: 421,
    price_level: 1,
    formatted_address: "전북 전주시 완산구 한벽로 33",
    distance_m: 520,
    reviews: [
      "두부 직접 만드시는 곳, 고소함이 다름.",
      "조용하고 차분한 분위기.",
      "노포 느낌이 좋음.",
    ],
    tags: ["두부", "노포", "고소"],
    hue: 100,
  },
  {
    id: "p8",
    name: "마당의 봄",
    category: "한식",
    rating: 4.8,
    user_ratings_total: 1102,
    price_level: 3,
    formatted_address: "전북 전주시 완산구 향교길 20",
    distance_m: 470,
    reviews: [
      "마당에서 식사하는 코스가 진짜 분위기 좋아요.",
      "데이트 분위기 만점, 예약 필수.",
      "감성 사진 찍기 최고.",
    ],
    tags: ["마당", "데이트", "감성", "프리미엄"],
    hue: 325,
  },
];

// keywords for natural-language parsing (rule-based) ----------------

const CATEGORIES = [
  { key: "한식",  words: ["한식", "한정식", "백반", "비빔밥", "전주 음식"] },
  { key: "양식",  words: ["양식", "파스타", "스테이크", "이탈리안"] },
  { key: "일식",  words: ["일식", "스시", "초밥", "라멘", "우동"] },
  { key: "중식",  words: ["중식", "짜장", "탕수육"] },
  { key: "카페",  words: ["카페", "디저트", "베이커리", "커피"] },
];

const PURPOSES = [
  { key: "친구",   words: ["친구", "동기", "친구랑"] },
  { key: "데이트", words: ["데이트", "여자친구", "남자친구", "연인"] },
  { key: "가족",   words: ["가족", "부모님", "엄마", "아빠"] },
  { key: "혼밥",   words: ["혼밥", "혼자", "나혼자"] },
  { key: "모임",   words: ["모임", "회식", "동아리"] },
];

function parseQuery(text) {
  const t = text.toLowerCase();

  // location: take phrase ending in "근처" or "주변", or known anchors
  let location = "전주 객사";
  const anchors = ["객사", "한옥마을", "남부시장", "전주역", "풍남문"];
  for (const a of anchors) if (text.includes(a)) { location = "전주 " + a; break; }
  const nearMatch = text.match(/([가-힣A-Za-z0-9 ]{2,}?)\s*(?:근처|주변|쪽)/);
  if (nearMatch) location = nearMatch[1].trim();

  // category
  let category = null;
  for (const c of CATEGORIES) if (c.words.some(w => text.includes(w))) { category = c.key; break; }

  // purpose
  let purpose = null;
  for (const p of PURPOSES) if (p.words.some(w => text.includes(w))) { purpose = p.key; break; }

  // price: 1 cheap, 2 mid, 3 expensive (max_price = upper bound)
  let max_price = 3;
  if (/(가성비|저렴|싸|싼|만원 이하|만원대)/.test(text)) max_price = 1;
  else if (/(너무 비싸지|적당|중간|합리|2만원대)/.test(text)) max_price = 2;
  else if (/(분위기 좋|프리미엄|고급|특별|기념|3만원)/.test(text)) max_price = 3;

  // atmosphere
  const need_atmosphere = /(분위기|감성|예쁜|인테리어|조용|아늑)/.test(text);

  return { location, category, max_price, need_atmosphere, purpose };
}

// agent search ------------------------------------------------------

const ATMO_WORDS = ["분위기","데이트","인테리어","감성","조용","아늑","예쁘","마당","한옥","한지"];

function atmosphereScore(place) {
  const blob = (place.reviews.join(" ") + " " + place.tags.join(" ")).toLowerCase();
  let score = 0;
  for (const w of ATMO_WORDS) if (blob.includes(w)) score += 1;
  return score;
}

function searchPlaces(state, opts = {}) {
  const minRating = opts.minRating ?? 4.3;
  const maxPrice  = opts.maxPrice  ?? state.max_price ?? 3;
  const maxDist   = opts.maxDist   ?? 500;

  let rows = PLACES.slice();
  if (state.category) rows = rows.filter(p => p.category === state.category);
  rows = rows.filter(p => p.rating >= minRating);
  rows = rows.filter(p => p.price_level <= maxPrice);
  rows = rows.filter(p => p.distance_m <= maxDist);

  rows = rows.map(p => ({ ...p, atmosphere_score: atmosphereScore(p) }));

  // sort
  rows.sort((a, b) => {
    if (state.need_atmosphere && a.atmosphere_score !== b.atmosphere_score)
      return b.atmosphere_score - a.atmosphere_score;
    if (a.rating !== b.rating) return b.rating - a.rating;
    return a.distance_m - b.distance_m;
  });

  return rows;
}

Object.assign(window, {
  PLACES, parseQuery, searchPlaces, atmosphereScore,
});
