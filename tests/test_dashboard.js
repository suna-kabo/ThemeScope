const assert = require("node:assert/strict");
const ui = require("../static/dashboard.js");

// Relative browsing must remain independent of daily scanner eligibility.
const measuredIneligible={weighted_vs_etf:"Outperforming",daily_stock_eligibility:{status:"ineligible",eligible:false,policy_version:"daily-stock-liquidity-2",reasons:["turnover_1d_usd:threshold_failed"]}};
assert.equal(ui.rsMatches(measuredIneligible,"Outperforming"),true);
assert.equal(ui.rsMatches(measuredIneligible,"Underperforming"),false);
assert.match(ui.dailyStockEligibilityText(measuredIneligible),/ineligible/);
assert.match(ui.dailyStockEligibilityText({}),/legacy\/unverified/);

// Grouping changes presentation only: preserve every original cell and its order.
const resultOrder=["Long bias","Selective long","Neutral","Selective short","Short bias","Unclassified"];
const matrixCells=[...resultOrder.slice().reverse(),"Neutral","Long bias"].map((direction,i)=>({direction,spy:i,qqq:null,breadth:null}));
const matrixBefore=JSON.stringify(matrixCells);
const matrixGroups=ui.groupMarketMatrix(matrixCells);
assert.deepEqual(matrixGroups.map(g=>g.result),resultOrder);
assert.equal(matrixGroups.flatMap(g=>g.cells).length,matrixCells.length);
assert.equal(new Set(matrixGroups.flatMap(g=>g.cells)).size,matrixCells.length);
for(const group of matrixGroups)assert.deepEqual(group.cells,matrixCells.filter(c=>c.direction===group.result));
assert.equal(JSON.stringify(matrixCells),matrixBefore);

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
    exchange: "Nasdaq Global Select Market", tradingview_symbol: "NASDAQ:AAA",
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
    exchange: "NYSE", tradingview_symbol: "NYSE:BBB",
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
    exchange: "NASDAQ", tradingview_symbol: "NASDAQ:AAA",
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
assert.match(csv, /return5_pct/);
assert.doesNotMatch(csv.split("\r\n")[0], /(?:^|,)return(?:5|21|63)(?:,|$)/);
const csvUnits = ui.rowsToCsv([{ticker:"U", returns:{"5":{value:0.1075}}, excess_returns:{"5":{value:0.0125}}}]);
assert.match(csvUnits, /10\.75/);
assert.match(csvUnits, /1\.25/);
const themeCsv = ui.themeRowsToCsv([{id:"u", name:"Unit", returns:{"21":{value:0.1075}}, excess_returns:{"21":{value:0.0125}}}], "2026-10-22", "generated");
assert.match(themeCsv.split("\r\n")[0], /return21_pct/);
assert.match(themeCsv.split("\r\n")[0], /theme_breadth21_above/);
assert.doesNotMatch(themeCsv.split("\r\n")[0], /(?:^|,)breadth21_above(?:,|$)/);
const themeCsvLines = themeCsv.split("\r\n");
assert.equal(themeCsvLines[0].split(",").length, themeCsvLines[1].split(",").length);
assert.equal(themeCsvLines[1].split(",")[themeCsvLines[0].split(",").indexOf('"theme_id"')], '"u"');
assert.equal(themeCsvLines[1].split(",")[themeCsvLines[0].split(",").indexOf('"return21_pct"')], '"10.75"');
assert.doesNotMatch(themeCsvLines[0], /excess21_pp|rank_t_minus_5|breadth21_change_5_pp/);
const tradingView = ui.tradingViewExport([rows[0], rows[1], rows[2]]);
assert.equal(tradingView.count, 2);
assert.equal(tradingView.duplicates, 1);
assert.equal(tradingView.omitted, 0);
assert.throws(() => ui.tradingViewExport([rows[3]]), /unresolved/);
assert.match(tradingView.text, /^NASDAQ:AAA,NYSE:BBB\n$/);
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
const expanded = ui.limitSelection(pool, 20);
assert.equal(expanded.length, 20);
assert.deepEqual(
  ui
    .sortRows(expanded, "adv30_usd", "asc")
    .map((r) => r.ticker)
    .sort(),
  expanded.map((r) => r.ticker).sort(),
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
assert.deepEqual(ui.resolvedScoreBands([]), configuredBands);
assert.deepEqual(ui.resolvedScoreBands([{class:"score-q1",min:0,max:100}]), configuredBands);
assert.equal(ui.breadthThresholdClass(50), "breadth-positive");
assert.equal(ui.breadthThresholdClass(49.999), "breadth-negative");
assert.equal(ui.breadthThresholdClass(null), "breadth-na");
assert.equal(ui.priorityCategory({research_priority:{category:"observation",group:3}}),"observation");
assert.equal(ui.priorityCategory({research_priority:{category:"primary",group:0,side:"long"}}),"primary");
assert.match(ui.directionClass("Short bias"), /direction-short/);
assert.match(ui.directionClass("Long bias"), /direction-long/);
assert.equal(ui.statusClass("Mixed"),"warning");
assert.equal(ui.labels.adv30_usd.label,"Avg $Vol30");
assert.match(ui.labels.adv30_usd.definition,/Price × Average Volume30/);
assert.equal(ui.marketCap(850e6),"$850M");
assert.equal(ui.marketCap(2.4e9),"$2.4B");
assert.equal(ui.marketCap(1.2e12),"$1.2T");
assert.equal(ui.marketCap(-1),"N/A");
assert.equal(ui.marketCap(null),"N/A");
assert.equal(ui.rsMatches({weighted_vs_etf:"Unavailable"},"Flat"),false);
assert.equal(ui.rsMatches({weighted_vs_etf:"Unavailable"},"All"),true);
assert.deepEqual(ui.sortRows([{id:"a",market_cap_usd:2.49e9},{id:"b",market_cap_usd:2.41e9}],"market_cap_usd","asc").map(r=>r.id),["b","a"]);

// Navigation is independent of daily metrics and research/performance ranking.
const navigationThemes=[{id:'one',name:'Pharmaceuticals',anchor:'XPH',tradingview_symbol:'AMEX:XPH',selected:[
 {ticker:'LLY',company:'Eli Lilly',tradingview_symbol:'NYSE:LLY',metric_status:'unavailable'},
 {ticker:'LLYX',company:'Prefix',tradingview_symbol:'NYSE:LLYX'},
 {ticker:'XLLYX',company:'Substring',tradingview_symbol:'NYSE:XLLYX'},
 {ticker:'ZZZ',company:'LLY Text',tradingview_symbol:'NYSE:ZZZ'}]},
 {id:'two',name:'Health Care',anchor:'XLV',tradingview_symbol:'AMEX:XLV',selected:[{ticker:'LLY',company:'Eli Lilly',tradingview_symbol:'NYSE:LLY'}]}];
const navigation=ui.buildNavigationIndex(navigationThemes);
assert.equal(navigation.filter(r=>r.kind==='stock'&&r.ticker==='LLY').length,2);
assert.deepEqual(ui.searchNavigation(navigation,'lly').map(r=>r.matchRank),[0,0,1,2,3]);
assert.equal(ui.searchNavigation(navigation,'XPH')[0].kind,'theme');
assert.equal(ui.searchNavigation(navigation,'Eli Lilly').filter(r=>r.kind==='stock').length,2);
assert.equal(ui.searchNavigation(navigation,'Health Care').length,2);
assert.deepEqual(ui.searchNavigation(navigation,'NOTFOUND'),[]);
assert.deepEqual(ui.searchNavigation(navigation,' '),[]);
assert.deepEqual(ui.searchNavigation(ui.buildNavigationIndex(navigationThemes.slice().reverse()),'LLY').map(r=>r.key),ui.searchNavigation(navigation,'LLY').map(r=>r.key));
assert.equal(ui.emaMatches({price_close:null,ema21:null},'above21'),false);
assert.equal(ui.emaMatches({price_close:10,ema21:10},'below21'),true);
assert.deepEqual(ui.sortRows([{id:'a',daily_change:.010001},{id:'b',daily_change:.010002},{id:'c',daily_change:null}], 'daily_change','desc').map(r=>r.id),['b','a','c']);
const dayCSV=ui.themeRowsToCsv([{id:'one',daily_change:.01234567}], '2026-10-30','test').split('\r\n');
assert.match(dayCSV[0],/"anchor_etf","change_1d_pct","priority_change"/);
assert.match(dayCSV[1],/"1.234567"/);

assert.equal(ui.emaRelationship(10,9),'Above');assert.equal(ui.emaRelationship(10,11),'Below');assert.equal(ui.emaRelationship(10,10),'At');
for(const invalid of [null,NaN,Infinity,0,-1,true]){assert.equal(ui.emaRelationship(invalid,10),'N/A');assert.equal(ui.emaRelationship(10,invalid),'N/A');}

for(const [date,expected] of [['2026-11-02','Today'],['2026-11-03','In 1 day'],['2027-01-01','In 60 days'],['2026-11-01','Past date'],['2026-02-30','N/A'],[null,'N/A']]) assert.equal(ui.earningsCountdown(date,'2026-11-02'),expected);
