const assert = require("node:assert/strict");
const ui = require("../static/dashboard.js");

const rows = [
  {
    ticker: "AAA",
    company: 'Alpha "One"',
    theme_name: "Semiconductors",
    selection_slot: 1,
    relative_state: "Outperforming",
    trend: "Uptrend",
    adv30_usd: 10,
    returns: { 21: { value: 0.1 } },
    excess_returns: { 21: { value: 0.02 } },
    exchange: "Nasdaq Global Select Market",
    theme_id: "semiconductors",
    theme_name: "Semiconductors",
  },
  {
    ticker: "BBB",
    company: "Beta",
    selection_slot: 2,
    relative_state: "Mixed",
    trend: "Mixed",
    adv30_usd: null,
    returns: { 21: { value: null } },
    excess_returns: { 21: { value: null } },
    exchange: "NYSE",
    theme_id: "cybersecurity",
    theme_name: "Cybersecurity",
  },
  {
    ticker: "AAA",
    company: "Alpha duplicate",
    selection_slot: 3,
    relative_state: "Outperforming",
    trend: "Uptrend",
    adv30_usd: 4,
    exchange: "NASDAQ",
    theme_id: "cybersecurity",
    theme_name: "Cybersecurity",
  },
  {
    ticker: "OTC",
    company: "Unmapped",
    selection_slot: 4,
    exchange: "OTC",
    theme_id: "other",
    theme_name: "Other",
  },
];

assert.equal(
  ui.filterRows(rows, { query: "cyber", relative: "All", trend: "All" }).length,
  2,
);
assert.deepEqual(
  ui.sortRows(rows, "adv30_usd", "desc").map((row) => row.ticker),
  ["AAA", "AAA", "BBB", "OTC"],
);
assert.deepEqual(
  ui.limitSelection(rows, 2).map((row) => row.selection_slot),
  [1, 2],
);
const csv = ui.rowsToCsv([rows[0]]);
assert.match(csv, /"Alpha ""One"""/);
assert.match(csv, /"semiconductors"/);
const tradingView = ui.tradingViewExport([rows[0], rows[1], rows[2], rows[3]]);
assert.equal(tradingView.count, 2);
assert.equal(tradingView.duplicates, 1);
assert.equal(tradingView.omitted, 1);
assert.match(tradingView.text, /^NASDAQ:AAA\nNYSE:BBB\n$/);
console.log("Dashboard interaction and export helpers passed.");
assert.deepEqual(
  ui.sortRows(rows, "adv30_usd", "asc").map((r) => r.adv30_usd),
  [4, 10, null, undefined],
);
let ranked = ui.ranked(
  [
    { ticker: "A", adv30_usd: 4 },
    { ticker: "B", adv30_usd: 4 },
    { ticker: "C", adv30_usd: null },
    { ticker: "D", adv30_usd: 2 },
  ],
  "adv30_usd",
  "desc",
);
assert.deepEqual(
  ranked.map((r) => r.display_rank),
  [1, 1, 3, null],
);
assert.equal(ui.filterRows(ranked, { query: "D" })[0].display_rank, 3);
const scores = [
  { id: "z", theme_score: null },
  { id: "b", theme_score: 60 },
  { id: "a", theme_score: 60 },
  { id: "c", theme_score: 10 },
];
assert.deepEqual(
  ui.sortRows(scores, "theme_score", "desc").map((r) => r.id),
  ["a", "b", "c", "z"],
);
assert.deepEqual(
  ui.sortRows(scores, "theme_score", "asc").map((r) => r.id),
  ["c", "a", "b", "z"],
);
assert.deepEqual(
  ui.sortRows([{ name: "Zebra" }, { name: "Apple" }], "name", "asc").map(
    (r) => r.name,
  ),
  ["Apple", "Zebra"],
);
assert.equal(
  ui.ranked(scores, "theme_score", "desc").at(-1).display_rank,
  null,
);
const pool = Array.from({ length: 25 }, (_, i) => ({
  ticker: "S" + i,
  selection_slot: i + 1,
  adv30_usd: 25 - i,
}));
const compact = ui.limitSelection(pool, 15),
  expanded = ui.limitSelection(pool, 20);
assert.equal(compact.length, 15);
assert.equal(expanded.length, 20);
assert.deepEqual(compact, expanded.slice(0, 15));
assert.deepEqual(
  ui
    .sortRows(compact, "adv30_usd", "asc")
    .map((r) => r.ticker)
    .sort(),
  compact.map((r) => r.ticker).sort(),
);
assert.match(
  ui.rowsToCsv([
    {
      ticker: "X",
      membership_tag: "Related",
      is_anchor_holding: false,
      etf_weight_pct: null,
    },
  ]),
  /membership_tag/,
);
const configuredBands = [
  { class: "score-q1", min: 0, max: 25 },
  { class: "score-q2", min: 25, max: 50 },
  { class: "score-q3", min: 50, max: 75 },
  { class: "score-q4", min: 75, max: 100 },
];
assert.equal(ui.scoreBandClass(24.999, configuredBands), "score-q1");
assert.equal(ui.scoreBandClass(25, configuredBands), "score-q2");
assert.equal(ui.scoreBandClass(49.999, configuredBands), "score-q2");
assert.equal(ui.scoreBandClass(50, configuredBands), "score-q3");
assert.equal(ui.scoreBandClass(74.999, configuredBands), "score-q3");
assert.equal(ui.scoreBandClass(75, configuredBands), "score-q4");
assert.equal(ui.scoreBandClass(100, configuredBands), "score-q4");
assert.equal(ui.scoreBandClass(null, configuredBands), "score-na");
