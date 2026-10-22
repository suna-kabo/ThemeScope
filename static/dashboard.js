(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ThemeScopeUI = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function valueAt(row, key) {
    if (key === "return21") return row.returns && row.returns["21"] && row.returns["21"].value;
    if (key === "return63") return row.returns && row.returns["63"] && row.returns["63"].value;
    if (key === "excess21") return row.excess_returns && row.excess_returns["21"] && row.excess_returns["21"].value;
    if (key === "excess63") return row.excess_returns && row.excess_returns["63"] && row.excess_returns["63"].value;
    return row[key];
  }

  function filterRows(rows, filters) {
    var query = String(filters.query || "").trim().toLowerCase();
    return rows.filter(function (row) {
      var textMatch = !query || [row.ticker, row.company, row.theme_name, row.evidence_note]
        .some(function (value) { return String(value || "").toLowerCase().includes(query); });
      var relativeMatch = !filters.relative || filters.relative === "All" || row.relative_state === filters.relative;
      var trendMatch = !filters.trend || filters.trend === "All" || row.trend === filters.trend;
      return textMatch && relativeMatch && trendMatch;
    });
  }

  function sortRows(rows, key, direction) {
    var sign = direction === "asc" ? 1 : -1;
    return rows.slice().sort(function (a, b) {
      var av = valueAt(a, key);
      var bv = valueAt(b, key);
      var aMissing = av === null || av === undefined || Number.isNaN(Number(av));
      var bMissing = bv === null || bv === undefined || Number.isNaN(Number(bv));
      if (aMissing !== bMissing) return aMissing ? 1 : -1;
      if (!aMissing && Number(av) !== Number(bv)) return sign * (Number(av) - Number(bv));
      return String(a.ticker || a.id || "").localeCompare(String(b.ticker || b.id || ""));
    });
  }

  function limitSelection(selected, limit) {
    return selected.slice().sort(function (a, b) { return a.selection_slot - b.selection_slot; }).slice(0, limit);
  }

  function csvEscape(value) {
    var text = value === null || value === undefined ? "" : String(value);
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function rowsToCsv(rows) {
    var header = ["theme", "theme_id", "selection_slot", "selection_queue", "ticker", "company", "exchange", "evidence_category", "evidence_note", "etf_weight_pct", "adv30_usd", "return21", "return63", "excess21_pp", "excess63_pp", "relative_state", "price_trend", "chart_url"];
    var columns = header;
    var lines = [header.map(csvEscape).join(",")];
    rows.forEach(function (row) {
      var values = {
        theme: row.theme_name,
        theme_id: row.theme_id,
        selection_slot: row.selection_slot,
        selection_queue: row.selection_queue,
        ticker: row.ticker,
        company: row.company,
        exchange: row.exchange,
        evidence_category: row.evidence_category,
        evidence_note: row.evidence_note,
        etf_weight_pct: row.etf_weight_pct,
        adv30_usd: row.adv30_usd,
        return21: valueAt(row, "return21"),
        return63: valueAt(row, "return63"),
        excess21_pp: valueAt(row, "excess21") === null || valueAt(row, "excess21") === undefined ? null : valueAt(row, "excess21") * 100,
        excess63_pp: valueAt(row, "excess63") === null || valueAt(row, "excess63") === undefined ? null : valueAt(row, "excess63") * 100,
        relative_state: row.relative_state,
        price_trend: row.trend,
        chart_url: row.chart_url
      };
      lines.push(columns.map(function (key) { return csvEscape(values[key]); }).join(","));
    });
    return lines.join("\r\n");
  }

  function tradingViewExport(rows) {
    var seen = new Set();
    var symbols = [];
    var omitted = 0;
    var duplicates = 0;
    rows.forEach(function (row) {
      var exchange = String(row.exchange || "").toUpperCase();
      var prefix = exchange.indexOf("NASDAQ") === 0 ? "NASDAQ" : (exchange.indexOf("NYSE") === 0 ? "NYSE" : "");
      if (!prefix) { omitted += 1; return; }
      var key = prefix + ":" + row.ticker;
      if (seen.has(key)) { duplicates += 1; return; }
      seen.add(key);
      symbols.push(key);
    });
    return { text: symbols.join("\n") + (symbols.length ? "\n" : ""), count: symbols.length, omitted: omitted, duplicates: duplicates };
  }

  function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function init(data) {
    var byId = new Map(data.themes.map(function (theme) { return [theme.id, theme]; }));
    var state = { themeId: data.themes[0] && data.themes[0].id, limit: 15, query: "", relative: "All", trend: "All", stockSort: "selection_slot", stockDirection: "asc", themeSort: "excess21", themeDirection: "desc" };
    var $ = function (selector) { return document.querySelector(selector); };
    var $$ = function (selector) { return Array.prototype.slice.call(document.querySelectorAll(selector)); };
    var fmtPct = function (metric) {
      if (!metric || metric.status !== "valid" || metric.value === null || metric.value === undefined) return '<span class="unavailable" title="' + escapeHtml(metric && metric.reason || "Unavailable") + '">Unavailable</span>';
      return (metric.value * 100).toFixed(1) + "%";
    };
    var fmtExcess = function (metric) {
      if (!metric || metric.status !== "valid" || metric.value === null || metric.value === undefined) return '<span class="unavailable" title="' + escapeHtml(metric && metric.reason || "Unavailable") + '">Unavailable</span>';
      var n = metric.value * 100;
      return (n > 0 ? "+" : "") + n.toFixed(1) + " pp";
    };
    var fmtMoney = function (value) {
      if (value === null || value === undefined || !Number.isFinite(Number(value))) return '<span class="unavailable">Unavailable</span>';
      var n = Number(value);
      if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
      if (n >= 1e9) return "$" + (n / 1e9).toFixed(1) + "B";
      if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
      return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
    };
    var badge = function (text, kind) { return '<span class="badge badge-' + escapeHtml(kind || "neutral") + '">' + escapeHtml(text || "Unavailable") + '</span>'; };
    var chartUrl = function (row) {
      var exchange = String(row.exchange || "").toUpperCase();
      var prefix = exchange.indexOf("NASDAQ") === 0 ? "NASDAQ" : (exchange.indexOf("NYSE") === 0 ? "NYSE" : "");
      return prefix ? "https://www.tradingview.com/chart/?symbol=" + encodeURIComponent(prefix + ":" + row.ticker) : "";
    };

    function selectedRows(theme) {
      return theme.selected.map(function (row) { return Object.assign({}, row, { theme_id: theme.id, theme_name: theme.name, chart_url: chartUrl(row) }); });
    }

    function activeRows() {
      var theme = byId.get(state.themeId);
      if (!theme) return [];
      var base = limitSelection(selectedRows(theme), state.limit);
      return sortRows(filterRows(base, { query: state.query, relative: state.relative, trend: state.trend }), state.stockSort, state.stockDirection);
    }

    function renderHeader() {
      var status = data.sources && data.sources.partial ? "Partial source retrieval" : "Live-source snapshot";
      $("#generatedAt").textContent = new Date(data.generated_at).toLocaleString();
      $("#sessionDate").textContent = data.session_date || "Unavailable";
      $("#runDate").textContent = data.run_date || "Unavailable";
      $("#globalStatus").innerHTML = badge(status, data.sources && data.sources.partial ? "warning" : "good");
      $("#registryVersion").textContent = data.registry_version || "—";
      $("#runId").textContent = data.run_id || "—";
      var complete = data.themes.filter(function (theme) { return theme.review_complete; }).length;
      $("#coverageSummary").textContent = data.themes.length + " ETF themes · " + complete + " complete membership reviews · full-universe breadth labels withheld where membership review is incomplete";
    }

    function renderContext() {
      $("#contextCards").innerHTML = data.context.map(function (item) {
        return '<article class="context-card"><div class="context-top"><span class="symbol">' + escapeHtml(item.ticker) + '</span>' + badge(item.trend, item.trend === "Uptrend" ? "positive" : item.trend === "Downtrend" ? "negative" : "neutral") + '</div>' +
          '<div class="context-values"><span>21 session <b>' + fmtPct(item.returns["21"]) + '</b></span><span>63 session <b>' + fmtPct(item.returns["63"]) + '</b></span></div><small>Absolute price trend · ' + escapeHtml(data.session_date || "") + '</small></article>';
      }).join("");
    }

    function renderThemes() {
      var sorted = sortRows(data.themes, state.themeSort, state.themeDirection);
      var html = sorted.map(function (theme) {
        var warning = theme.review_complete ? "Reviewed" : "Review incomplete";
        var b = theme.breadth.above_ema21;
        var breadth = b.valid_count ? b.count + "/" + b.valid_count + " (" + (b.fraction * 100).toFixed(0) + "%) · reviewed subset" : "Unavailable";
        var warnings = [warning];
        if (theme.holdings_status !== "current") warnings.push("Holdings " + theme.holdings_status);
        if (!theme.anchor_screen.anchor_screen_valid) warnings.push("Anchor screen incomplete");
        return '<tr class="theme-row ' + (theme.id === state.themeId ? 'is-selected' : '') + '" data-theme-id="' + escapeHtml(theme.id) + '" tabindex="0">' +
          '<td><b>' + escapeHtml(theme.name) + '</b><small>' + escapeHtml(theme.anchor) + (theme.parent_sector ? ' · parent ' + escapeHtml(theme.parent_sector) : '') + '</small></td>' +
          '<td>' + fmtPct(theme.returns["21"]) + '</td><td>' + fmtExcess(theme.excess_returns["21"]) + '</td><td>' + fmtPct(theme.returns["63"]) + '</td><td>' + fmtExcess(theme.excess_returns["63"]) + '</td>' +
          '<td>' + badge(theme.relative_state, theme.relative_state === "Outperforming" ? "positive" : theme.relative_state === "Underperforming" ? "negative" : "neutral") + '</td>' +
          '<td>' + badge(theme.trend, theme.trend === "Uptrend" ? "positive" : theme.trend === "Downtrend" ? "negative" : "neutral") + '</td>' +
          '<td>' + escapeHtml(breadth) + '<small>' + escapeHtml(b.label === "Unavailable" ? b.label_reason || "Summary label unavailable" : b.label) + '</small></td>' +
          '<td class="count-cell">' + theme.official_holdings_count + ' position rows / ' + theme.official_unique_ticker_count + ' tickers · ' + theme.eligible_reviewed_count + ' provisional eligible · ' + theme.selected.length + ' pool / ' + Math.min(15, theme.selected.length) + ' compact</td>' +
          '<td>' + warnings.map(function (v) { return badge(v, v === "Reviewed" ? "good" : "warning"); }).join(" ") + '</td></tr>';
      }).join("");
      $("#themeRows").innerHTML = html || '<tr><td colspan="10">No theme data was retrieved.</td></tr>';
      $$(".theme-row").forEach(function (row) {
        var choose = function () { state.themeId = row.dataset.themeId; renderThemes(); renderActiveTheme(); };
        row.addEventListener("click", choose);
        row.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); } });
      });
    }

    function renderBreadth(theme) {
      var b = theme.breadth;
      function one(label, item, percent) {
        var value = item.fraction === null || item.fraction === undefined ? "Unavailable" : item.count + "/" + item.valid_count + " · " + (item.fraction * 100).toFixed(1) + "%";
        var cov = item.coverage === null || item.coverage === undefined ? "No eligible denominator" : "Coverage " + (item.coverage * 100).toFixed(0) + "% of " + item.eligible_count;
        var unquantified = "Reviewed, unquantified: " + (item.reviewed_unquantified_valid_count || 0) + " valid / " + (item.reviewed_unquantified_eligible_count || 0) + " eligible";
        return '<div class="breadth-item"><span>' + escapeHtml(label) + '</span><b>' + escapeHtml(value) + '</b><small>' + escapeHtml(cov) + '</small><small>' + escapeHtml(unquantified) + '</small></div>';
      }
      var median = b.median_return21.value === null ? "Unavailable" : (b.median_return21.value * 100).toFixed(1) + "%";
      return '<div class="breadth-grid">' + one("Above EMA21", b.above_ema21, true) + one("Above EMA50", b.above_ema50, true) + one("Uptrend", b.uptrend, true) + '<div class="breadth-item"><span>Median Return21</span><b>' + escapeHtml(median) + '</b><small>' + b.median_return21.valid_count + "/" + b.median_return21.eligible_count + ' returns · reviewed subset</small></div></div>' +
        '<div class="breadth-warning">' + badge("Summary label: " + (b.above_ema21.label || "Unavailable"), "warning") + ' ' + escapeHtml(b.above_ema21.label_reason || theme.review_reason || "Membership review is incomplete") + '</div>';
    }

    function renderActiveTheme() {
      var theme = byId.get(state.themeId);
      if (!theme) return;
      $("#activeThemeName").textContent = theme.name;
      $("#activeThemeSubtitle").textContent = theme.anchor + " · holdings as of " + (theme.holdings_source.as_of || "unavailable") + " · " + theme.official_holdings_count + " position rows / " + theme.official_unique_ticker_count + " unique tickers";
      $("#activeThemeRationale").textContent = theme.anchor_rationale;
      $("#activeThemeScope").textContent = theme.scope;
      $("#activeThemeReview").innerHTML = badge(theme.review_complete ? "Complete membership review" : "Incomplete membership review", theme.review_complete ? "good" : "warning") + ' ' + escapeHtml(theme.review_reason || "Only the provisional reviewed subset is in candidate selection.");
      var criteria = theme.anchor_screen.anchor_criteria || {};
      $("#anchorScreenNote").innerHTML = '<b>Anchor checks:</b> 64 consecutive sessions ' + badge(criteria.history_64_sessions ? "pass" : "unavailable", criteria.history_64_sessions ? "good" : "warning") + ' · ADV$30 ≥ $1M ' + badge(criteria.adv30_at_least_1m ? "pass" : "unavailable", criteria.adv30_at_least_1m ? "good" : "warning") + ' · USD equity ETF / mandate review ' + badge(criteria.usd_unleveraged_equity_etf_mandate ? "pass" : "unavailable", criteria.usd_unleveraged_equity_etf_mandate ? "good" : "warning") + '<small> ' + escapeHtml(theme.anchor_screen.mandate_review_note || "Mandate review detail unavailable") + '</small>';
      $("#activeBreadth").innerHTML = renderBreadth(theme);
      $("#holdingsFreshness").textContent = theme.holdings_status === "current" ? "Current · " + theme.holdings_age_days + " days old" : "Unavailable or stale";
      $("#coverageWeights").innerHTML = '<span>Reviewed eligible holdings <b>' + (theme.eligible_weight_pct || 0).toFixed(1) + '%</b></span><span>Selected pool <b>' + (theme.selected_weight_pct || 0).toFixed(1) + '%</b></span><span>Visible first 15 <b>' + (theme.visible15_weight_pct || 0).toFixed(1) + '%</b></span><span>Largest / top five holding <b>' + (theme.largest_holding_weight_pct === null ? "Unavailable" : theme.largest_holding_weight_pct.toFixed(1) + "%") + ' / ' + (theme.top5_holding_weight_pct === null ? "Unavailable" : theme.top5_holding_weight_pct.toFixed(1) + "%") + '</b></span><small>Fund net-asset weights, not renormalized; reviewed subset only. ' + theme.pending_count + ' holdings pending; ' + theme.stale_evidence_count + ' newer annual filings require review; ' + theme.unavailable_evidence_freshness_count + ' SEC checks unavailable.</small>';
      var comps = theme.anchor_comparisons || [];
      $("#anchorComparisons").innerHTML = comps.length ? comps.map(function (c) {
        return '<article class="comparison-card"><b>' + escapeHtml(c.ticker) + '</b> ' + escapeHtml(c.provider) + '<p>' + escapeHtml(c.comparison_note) + '</p><small>Holdings ' + escapeHtml(c.holdings_as_of || "unavailable") + ' · ' + c.holdings_count + ' holdings · Return21 ' + fmtPct(c.returns["21"]) + ' · ADV$30 ' + fmtMoney(c.adv30_usd) + ' · top-five weight ' + (c.top5_weight_pct === null ? "Unavailable" : c.top5_weight_pct.toFixed(1) + "%") + '</small></article>';
      }).join("") : '<span class="muted">No alternate anchor was included in this run.</span>';
      if (theme.parent_comparison) {
        var p = theme.parent_comparison;
        $("#parentComparison").innerHTML = '<b>' + escapeHtml(p.ticker) + '</b> parent-sector context · Return21 ' + fmtPct(p.returns["21"]) + ' · Return63 ' + fmtPct(p.returns["63"]) + ' · Excess21 vs theme ' + fmtExcess(p.excess_returns["21"]) + ' · price trend ' + badge(p.trend, "neutral");
      } else {
        $("#parentComparison").textContent = "No parent-sector ETF is assigned for this theme.";
      }
      renderStocks();
      renderExplorer(theme);
      renderPending(theme);
    }

    function renderStocks() {
      var theme = byId.get(state.themeId);
      var rows = activeRows();
      $("#stockCount").textContent = rows.length + " visible of " + Math.min(state.limit, theme.selected.length) + " selected slots · " + theme.eligible_reviewed_count + " eligible in the reviewed subset";
      $("#stockReviewNotice").innerHTML = badge("Provisional candidates", "warning") + ' Filters and sorting do not add or remove selections. The pool is limited to screened current ETF holdings; ' + theme.pending_count + ' holdings remain pending.';
      $("#stockRows").innerHTML = rows.map(function (row) {
        var isState = row.relative_state;
        var ret21 = row.returns && row.returns["21"];
        var ret63 = row.returns && row.returns["63"];
        var ex21 = row.excess_returns && row.excess_returns["21"];
        var ex63 = row.excess_returns && row.excess_returns["63"];
        var chart = row.chart_url ? '<a class="chart-link" target="_blank" rel="noopener" href="' + escapeHtml(row.chart_url) + '">Chart ↗</a>' : '<span class="unavailable">No exchange map</span>';
        var why = row.eligibility_reasons && row.eligibility_reasons.length ? row.eligibility_reasons.join("; ") : row.evidence_note;
        return '<tr><td><b>' + escapeHtml(row.ticker) + '</b><small>' + escapeHtml(row.company) + '</small><small>' + escapeHtml(row.theme_name) + ' · ' + escapeHtml(row.anchor) + '</small><small>Selection: ' + escapeHtml(row.selection_reason || "Queue order browsing convention") + '</small>' + chart + '</td>' +
          '<td>' + escapeHtml(row.evidence_category) + '<small>' + escapeHtml(row.evidence_note) + '</small></td>' +
          '<td class="num" title="' + escapeHtml(row.adv30_metric && row.adv30_metric.reason) + '">' + fmtMoney(row.adv30_usd) + '</td>' +
          '<td class="num" title="' + escapeHtml(ret21 && ret21.reason) + '">' + fmtPct(ret21) + '</td><td class="num" title="' + escapeHtml(ret63 && ret63.reason) + '">' + fmtPct(ret63) + '</td>' +
          '<td class="num" title="' + escapeHtml(ex21 && ex21.reason) + '">' + fmtExcess(ex21) + '</td><td class="num" title="' + escapeHtml(ex63 && ex63.reason) + '">' + fmtExcess(ex63) + '</td>' +
          '<td>' + badge(isState, isState === "Outperforming" ? "positive" : isState === "Underperforming" ? "negative" : "neutral") + '</td>' +
          '<td>' + badge(row.trend, row.trend === "Uptrend" ? "positive" : row.trend === "Downtrend" ? "negative" : "neutral") + '<small>' + escapeHtml(row.trend_reason || "") + '</small></td>' +
          '<td title="' + escapeHtml(row.market_cap_freshness) + '">' + (row.market_cap_usd === null ? '<span class="unavailable">Unavailable</span>' : fmtMoney(row.market_cap_usd)) + '<small>' + escapeHtml(row.industry || "Industry unavailable") + '</small><small class="data-caveat">Field timestamp unavailable · retrieved ' + escapeHtml(row.market_cap_retrieved_at || "unavailable") + '</small></td>' +
          '<td><details><summary>Evidence</summary><p>' + escapeHtml(row.evidence_note) + '</p><p>' + escapeHtml(row.evidence && row.evidence.excerpt || "") + '</p><a target="_blank" rel="noopener" href="' + escapeHtml(row.evidence && row.evidence.url || "#") + '">' + escapeHtml(row.evidence && row.evidence.form || "SEC filing") + ' · filed ' + escapeHtml(row.evidence && row.evidence.filed_date || "") + '</a><small>Evidence checked ' + escapeHtml(row.reviewed_date || "date unavailable") + ' · membership weight ' + (row.etf_weight_pct === null ? "Unavailable" : row.etf_weight_pct.toFixed(2) + "%") + ' · ' + escapeHtml(row.security_type) + '</small><small>' + escapeHtml(row.security_mapping_note || "") + '</small><small>Annual filing check: ' + escapeHtml(row.evidence_freshness && row.evidence_freshness.reason || "Unavailable") + '</small></details></td></tr>';
      }).join("") || '<tr><td colspan="11" class="empty-state">No stock rows pass the current reviewed-subset filters. ETF return data remains separate.</td></tr>';
    }

    function renderExplorer(theme) {
      var rows = theme.reviewed_universe.map(function (row) { return Object.assign({}, row, { theme_id: theme.id, theme_name: theme.name }); });
      var filtered = filterRows(rows, { query: state.query, relative: "All", trend: "All" });
      $("#explorerCount").textContent = filtered.length + " eligible reviewed companies · full theme universe not screened";
      $("#explorerRows").innerHTML = filtered.map(function (row) {
        return '<tr><td>' + escapeHtml(row.ticker) + '</td><td>' + escapeHtml(row.company) + '</td><td>' + fmtMoney(row.market_cap_usd) + '</td><td>' + fmtMoney(row.adv30_usd) + '</td><td>' + fmtExcess(row.excess_returns && row.excess_returns["21"]) + '</td><td>' + badge(row.relative_state, "neutral") + '</td><td>' + badge(row.trend, "neutral") + '</td><td>' + escapeHtml((row.share_classes || []).join(", ")) + '</td></tr>';
      }).join("") || '<tr><td colspan="8" class="empty-state">No eligible reviewed companies.</td></tr>';
    }

    function renderPending(theme) {
      var rows = theme.pending_holdings || [];
      $("#pendingCount").textContent = rows.length + " official holdings pending issuer review or mapping";
      $("#pendingRows").innerHTML = rows.map(function (row) {
        var evidence = row.evidence ? '<details><summary>Evidence</summary><p>' + escapeHtml(row.evidence.excerpt || "") + '</p><a target="_blank" rel="noopener" href="' + escapeHtml(row.evidence.url || "#") + '">' + escapeHtml(row.evidence.form || "SEC filing") + ' · filed ' + escapeHtml(row.evidence.filed_date || "") + '</a><small>Reviewed ' + escapeHtml(row.reviewed_date || "date unavailable") + ' · category ' + escapeHtml(row.evidence_category || "") + '</small></details>' : '';
        return '<tr><td>' + escapeHtml(row.ticker) + '</td><td>' + escapeHtml(row.company) + '</td><td>' + (row.weight_pct === null ? "Unavailable" : Number(row.weight_pct).toFixed(2) + "%") + '</td><td>' + escapeHtml(row.status) + '</td><td>' + escapeHtml(row.reason) + evidence + '</td></tr>';
      }).join("") || '<tr><td colspan="5" class="empty-state">No unresolved official holdings in this snapshot.</td></tr>';
      var exclusions = theme.exclusions || [];
      $("#excludedCount").textContent = exclusions.length + " reviewed membership/data exclusions";
      $("#excludedRows").innerHTML = exclusions.map(function (row) {
        var evidence = row.evidence ? '<details><summary>Evidence / freshness</summary><p>' + escapeHtml(row.evidence.excerpt || "") + '</p><a target="_blank" rel="noopener" href="' + escapeHtml(row.evidence.url || "#") + '">' + escapeHtml(row.evidence.form || "SEC filing") + ' · filed ' + escapeHtml(row.evidence.filed_date || "") + '</a><small>' + escapeHtml(row.evidence_freshness && row.evidence_freshness.reason || "") + '</small></details>' : '';
        return '<tr><td>' + escapeHtml(row.ticker) + '</td><td>' + escapeHtml(row.company) + '</td><td>' + (row.weight_pct === null ? "Unavailable" : Number(row.weight_pct).toFixed(2) + "%") + '</td><td>' + escapeHtml((row.reasons || []).join("; ")) + evidence + '</td></tr>';
      }).join("") || '<tr><td colspan="4" class="empty-state">No exclusions recorded for the reviewed subset.</td></tr>';
    }

    function download(name, text, type) {
      var blob = new Blob([text], { type: type || "text/plain;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.href = url;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function renderActiveThemeAndCounts() {
      renderThemes();
      renderActiveTheme();
    }

    $$("[data-theme-sort]").forEach(function (button) {
      button.addEventListener("click", function () {
        var key = button.dataset.themeSort;
        state.themeDirection = state.themeSort === key && state.themeDirection === "desc" ? "asc" : "desc";
        state.themeSort = key;
        renderThemes();
      });
    });
    $$("[data-stock-sort]").forEach(function (button) {
      button.addEventListener("click", function () {
        var key = button.dataset.stockSort;
        state.stockDirection = state.stockSort === key && state.stockDirection === "asc" ? "desc" : "asc";
        state.stockSort = key;
        renderStocks();
      });
    });
    $$("[data-limit]").forEach(function (button) {
      button.addEventListener("click", function () {
        state.limit = Number(button.dataset.limit);
        $$("[data-limit]").forEach(function (other) { other.classList.toggle("active", other === button); });
        renderStocks();
      });
    });
    $("#stockSearch").addEventListener("input", function (event) { state.query = event.target.value; renderStocks(); renderExplorer(byId.get(state.themeId)); });
    $("#relativeFilter").addEventListener("change", function (event) { state.relative = event.target.value; renderStocks(); });
    $("#trendFilter").addEventListener("change", function (event) { state.trend = event.target.value; renderStocks(); });
    $("#resetFilters").addEventListener("click", function () {
      state.query = ""; state.relative = "All"; state.trend = "All"; state.limit = 15; state.stockSort = "selection_slot"; state.stockDirection = "asc";
      $("#stockSearch").value = ""; $("#relativeFilter").value = "All"; $("#trendFilter").value = "All";
      $$("[data-limit]").forEach(function (button) { button.classList.toggle("active", Number(button.dataset.limit) === 15); });
      renderStocks(); renderExplorer(byId.get(state.themeId));
    });
    $("#exportCsv").addEventListener("click", function () {
      var rows = activeRows();
      download("themescope-filtered-watchlist.csv", rowsToCsv(rows), "text/csv;charset=utf-8");
      $("#exportStatus").textContent = "CSV exported: " + rows.length + " filtered rows from the active theme; the theme column is retained.";
    });
    $("#exportTradingView").addEventListener("click", function () {
      var result = tradingViewExport(activeRows());
      download("themescope-tradingview-watchlist.txt", result.text, "text/plain;charset=utf-8");
      $("#exportStatus").textContent = "TradingView text exported: " + result.count + " exchange-qualified symbols; " + result.duplicates + " duplicate rows collapsed and " + result.omitted + " rows without a verified exchange were omitted. Text import is flat; it does not preserve theme sections.";
    });

    renderHeader();
    renderContext();
    renderActiveThemeAndCounts();
    var sourceRows = (data.source_matrix || []).map(function (source) {
      var url = source.url ? '<a target="_blank" rel="noopener" href="' + escapeHtml(source.url) + '">Open source ↗</a>' : 'Unavailable';
      return '<tr><td><b>' + escapeHtml(source.field) + '</b><small>' + escapeHtml(source.scope || "") + '</small></td><td>' + escapeHtml(source.provider) + '<small>' + escapeHtml(source.method) + '</small></td><td>' + escapeHtml(source.history_or_as_of) + '</td><td>' + escapeHtml(source.delay_and_availability) + '</td><td>' + escapeHtml(source.limitations) + '</td><td>' + escapeHtml(source.fallback) + '</td><td>' + escapeHtml(source.last_test) + '</td><td>' + escapeHtml(source.retrieved_at || "Not retrieved this run") + '</td><td>' + url + '</td></tr>';
    }).join("");
    $("#sourceRows").innerHTML = sourceRows;
    $("#sourceMatrixNote").textContent = "Source retrievals that fail are shown as unavailable in the tables and run report; the generator never reuses an old snapshot as current. SEC annual filing dates are rechecked on every run. SEC 8-K disclosures are not automatically classified.";
    $("#footerRun").textContent = "Run " + (data.run_id || "—") + " · session " + (data.session_date || "Unavailable") + " · generated " + (data.generated_at || "Unavailable");
  }

  return {
    valueAt: valueAt,
    filterRows: filterRows,
    sortRows: sortRows,
    limitSelection: limitSelection,
    rowsToCsv: rowsToCsv,
    tradingViewExport: tradingViewExport,
    init: init
  };
});
