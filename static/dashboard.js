(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ThemeScopeUI = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function valueAt(row, key) {
    if (key === "return5")
      return row.returns && row.returns["5"] && row.returns["5"].value;
    if (key === "return21")
      return row.returns && row.returns["21"] && row.returns["21"].value;
    if (key === "return63")
      return row.returns && row.returns["63"] && row.returns["63"].value;
    if (key === "excess5")
      return row.excess_returns && row.excess_returns["5"] && row.excess_returns["5"].value;
    if (key === "excess21")
      return (
        row.excess_returns &&
        row.excess_returns["21"] &&
        row.excess_returns["21"].value
      );
    if (key === "excess63")
      return (
        row.excess_returns &&
        row.excess_returns["63"] &&
        row.excess_returns["63"].value
      );
    return row[key];
  }

  function filterRows(rows, filters) {
    var query = String(filters.query || "")
      .trim()
      .toLowerCase();
    return rows.filter(function (row) {
      var textMatch =
        !query ||
        [row.ticker, row.anchor, row.name, row.company, row.theme_name, row.evidence_note].some(
          function (value) {
            return String(value || "")
              .toLowerCase()
              .includes(query);
          },
        );
      var relativeMatch =
        !filters.relative ||
        filters.relative === "All" ||
        row.relative_state === filters.relative;
      var trendMatch =
        !filters.trend ||
        filters.trend === "All" ||
        row.trend === filters.trend;
      return textMatch && relativeMatch && trendMatch;
    });
  }

  function sortRows(rows, key, direction) {
    if (key === "priority") return rows.slice().sort(function(a,b) { var x=a.research_priority || {}, y=b.research_priority || {}; return (x.group ?? 3)-(y.group ?? 3) || ((x.side === "short" ? a.theme_score-b.theme_score : b.theme_score-a.theme_score) || String(a.id).localeCompare(String(b.id))); });
    var sign = direction === "asc" ? 1 : -1;
    return rows.slice().sort(function (a, b) {
      var av = valueAt(a, key);
      var bv = valueAt(b, key);
      var aText =
          typeof av === "string" &&
          av.trim() !== "" &&
          !Number.isFinite(Number(av)),
        bText =
          typeof bv === "string" &&
          bv.trim() !== "" &&
          !Number.isFinite(Number(bv)),
        aMissing =
          av === null ||
          av === undefined ||
          (typeof av === "string" && av.trim() === "") ||
          (!aText && !Number.isFinite(Number(av))),
        bMissing =
          bv === null ||
          bv === undefined ||
          (typeof bv === "string" && bv.trim() === "") ||
          (!bText && !Number.isFinite(Number(bv)));
      if (aMissing !== bMissing) return aMissing ? 1 : -1;
      if (!aMissing && !bMissing && aText && bText) {
        var textOrder = av.localeCompare(bv);
        if (textOrder) return sign * textOrder;
      }
      if (!aMissing && Number(av) !== Number(bv))
        return sign * (Number(av) - Number(bv));
      return String(a.id || a.ticker || "").localeCompare(
        String(b.id || b.ticker || ""),
      );
    });
  }

  function limitSelection(selected, limit) {
    return selected
      .slice()
      .sort(function (a, b) {
        return a.selection_slot - b.selection_slot;
      })
      .slice(0, limit);
  }

  function csvEscape(value) {
    var text = value === null || value === undefined ? "" : String(value);
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function finiteNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  var DEFAULT_SCORE_BANDS = [
    { min: 0, max: 25, class: "score-q1" },
    { min: 25, max: 50, class: "score-q2" },
    { min: 50, max: 75, class: "score-q3" },
    { min: 75, max: 100, class: "score-q4" },
  ];

  function validScoreBands(bands) {
    if (!Array.isArray(bands) || bands.length !== 4) return false;
    var ordered = bands.slice().sort(function (a, b) { return a.min - b.min; });
    return ordered[0].min === 0 && ordered[ordered.length - 1].max === 100 && ordered.every(function (band, index) {
      return finiteNumber(band.min) && finiteNumber(band.max) && band.min < band.max && /^score-q[1-4]$/.test(band.class) && (index === 0 || ordered[index - 1].max === band.min);
    });
  }

  function resolvedScoreBands(bands) {
    return validScoreBands(bands) ? bands.slice().sort(function (a, b) { return a.min - b.min; }) : DEFAULT_SCORE_BANDS;
  }

  function scoreBandClass(value, bands) {
    if (!finiteNumber(value)) return "score-na";
    var band = (bands || []).find(function (item) {
      return value >= item.min && (value < item.max || item.max === 100 && value <= 100);
    });
    return band ? band.class : "score-na";
  }

  function breadthThresholdClass(value) {
    return !finiteNumber(value) ? "breadth-na" : value >= 50 ? "breadth-positive" : "breadth-negative";
  }

  var LABELS = {
    rs_state:{label:"RS browsing filter",definition:"Outperforming: stock minus selected ETF differences are both strictly positive on 1M and 3M. Underperforming: both strictly negative. Mixed: other valid pairs, including equality. Missing inputs remain separate. Browsing only; no membership or priority changes."},
    market_cap_usd:{label:"Market Cap",definition:"Company market capitalization in USD from the supplied Stock CSV. Compact display; sorting uses the original numeric value."},
    excess21_pp:{label:"1M vs ETF (pp)",definition:"Stock TradingView 1M Performance minus selected anchor ETF 1M Performance, in percentage points; not ratio growth."},
    excess63_pp:{label:"3M vs ETF (pp)",definition:"Stock TradingView 3M Performance minus selected anchor ETF 3M Performance, in percentage points; not ratio growth."},
    adv30_usd: {label:"Avg $Vol30", definition:"TradingView Price × Average Volume30; not the mean of daily Close × Volume."},
    turnover_1d_usd: {label:"Turnover 1D", definition:"TradingView Price × Volume for one day; not an independently verified sum of trades."},
    atr14_pct: {label:"ATR%14", definition:"TradingView daily average true range percent over 14 periods; volatility context, not expected return."},
    relative_volume_1d: {label:"Rel Vol", definition:"TradingView relative volume for one day; a multiple, not a percentage return."}
  };
  function directionClass(value) {
    return {"Long bias":"direction-long", "Selective long":"direction-long direction-selective", "Neutral":"direction-neutral", "Selective short":"direction-short direction-selective", "Short bias":"direction-short", "Unclassified":"direction-unavailable"}[value] || "direction-unavailable";
  }
  function statusClass(value) {
    return ["Bullish","Positive"].includes(value) ? "positive" : ["Bearish","Negative"].includes(value) ? "negative" : value === "Mixed" ? "warning" : "muted";
  }
  function priorityCategory(row) { return row.research_priority?.category || "watch"; }
  function marketCap(value) {
    if (!finiteNumber(value) || value <= 0) return "N/A";
    var unit = value >= 1e12 ? [1e12,"T"] : value >= 1e9 ? [1e9,"B"] : value >= 1e6 ? [1e6,"M"] : [1,""];
    return "$" + (value/unit[0]).toLocaleString("en-US",{maximumFractionDigits:1}) + unit[1];
  }
  function rsMatches(row, filter) { return !filter || filter === "All" || row.rs_state === filter; }
  function emaRelationship(price,average) {
    if(!finiteNumber(price) || !finiteNumber(average) || price<=0 || average<=0)return 'N/A';
    return price>average?'Above':price<average?'Below':'At';
  }
  function emaMatches(row, filter) {
    if (!filter || filter === "all") return true;
    var period=filter.endsWith("21")?21:50;
    if (!finiteNumber(row.price_close) || !finiteNumber(row["ema"+period])) return false;
    return filter.startsWith("above")?row.price_close>row["ema"+period]:row.price_close<=row["ema"+period];
  }
  function buildNavigationIndex(themes) {
    var index=[];
    (themes || []).forEach(function(theme){
      var context={themeId:theme.id,themeName:theme.name,anchor:theme.anchor};
      index.push(Object.assign({kind:"theme",key:"theme:"+theme.id,ticker:theme.anchor,symbol:theme.tradingview_symbol},context));
      var seen=new Set();
      (theme.selected || []).forEach(function(stock){
        if(!stock.tradingview_symbol || seen.has(stock.tradingview_symbol))return;
        seen.add(stock.tradingview_symbol);
        index.push(Object.assign({kind:"stock",key:"stock:"+theme.id+":"+stock.tradingview_symbol,ticker:stock.ticker,symbol:stock.tradingview_symbol,company:stock.company || ""},context));
      });
    });
    return index;
  }
  function searchNavigation(index, query) {
    var q=String(query || "").trim().toLowerCase();
    if(!q)return [];
    return index.map(function(row){
      var tickers=[row.ticker].map(function(s){return String(s || "").toLowerCase();});
      var rank=tickers.some(function(s){return s===q;})?0:tickers.some(function(s){return s.startsWith(q);})?1:tickers.some(function(s){return s.includes(q);})?2:
        [row.company,row.themeName,row.symbol].some(function(s){return String(s || "").toLowerCase().includes(q);})?3:null;
      return Object.assign({matchRank:rank},row);
    }).filter(function(row){return row.matchRank!==null;}).sort(function(a,b){
      return a.matchRank-b.matchRank || (a.ticker || "").localeCompare(b.ticker || "","en") || a.themeName.localeCompare(b.themeName,"en") || a.key.localeCompare(b.key,"en");
    });
  }
  function themeRowsToCsv(rows, session, generatedAt) {
    var columns = ["rank_current", "rank_change_daily", "type", "theme_id", "name", "anchor_etf", "change_1d_pct", "priority_change", "research_priority", "vs_ema21", "vs_ema50", "theme_score", "current_strength", "medium_strength", "return5_pct", "return21_pct", "return63_pct", "theme_breadth21_pct", "theme_breadth21_above", "theme_breadth21_valid", "theme_breadth50_pct", "theme_breadth50_above", "theme_breadth50_valid", "configured_watchlist_count", "session_date", "generated_at"];
    var lines = [columns.map(csvEscape).join(",")];
    rows.forEach(function (row) {
      var b21 = row.theme_watchlist_breadth && row.theme_watchlist_breadth["21"] || {};
      var b50 = row.theme_watchlist_breadth && row.theme_watchlist_breadth["50"] || {};
      var values = [row.rank_current ?? row.global_rank, row.rank_change_daily,
        row.level === "Sector" ? "Sector" : "Theme", row.id, row.name, row.anchor, finiteNumber(row.daily_change)?row.daily_change*100:null, row.priority_change, row.research_priority?.label, emaRelationship(row.price_close,row.ema21), emaRelationship(row.price_close,row.ema50),
        row.theme_score, row.current_strength_score, row.medium_strength_score,
        finiteNumber(valueAt(row, "return5")) ? valueAt(row, "return5") * 100 : null,
        finiteNumber(valueAt(row, "return21")) ? valueAt(row, "return21") * 100 : null,
        finiteNumber(valueAt(row, "return63")) ? valueAt(row, "return63") * 100 : null,
        row.theme_breadth21_pct, row.theme_breadth21_above ?? b21.above_count, row.theme_breadth21_valid ?? b21.valid_count,
        row.theme_breadth50_pct, row.theme_breadth50_above ?? b50.above_count, row.theme_breadth50_valid ?? b50.valid_count,
        row.configured_watchlist_count, session, generatedAt];
      lines.push(values.map(csvEscape).join(","));
    });
    return lines.join("\r\n");
  }

  function rowsToCsv(rows) {
    var header = [
      "theme",
      "theme_id",
      "session_date",
      "generated_at",
      "visible_rank",
      "price_close",
      "market_cap_usd",
      "anchor_etf",
      "anchor_performance_1m_pct",
      "anchor_performance_3m_pct",
      "return5_pct",
      "excess5_pp",
      "selection_slot",
      "selection_queue",
      "ticker",
      "company",
      "exchange",
      "membership_tag",
      "membership_rationale",
      "above_ema21",
      "above_ema50",
      "ema21",
      "ema50",
      "adv30_usd",
      "return21_pct",
      "return63_pct",
      "excess21_pp",
      "excess63_pp",
      "relative_state",
      "price_trend",
      "chart_url",
    ];
    var columns = header;
    var lines = [header.map(csvEscape).join(",")];
    rows.forEach(function (row) {
      var values = {
        theme: row.theme_name,
        session_date: row.session_date,
        generated_at: row.generated_at,
        visible_rank: row.display_rank,
        price_close: row.price_close,
        market_cap_usd: row.market_cap_usd,
        anchor_etf: row.anchor,
        anchor_performance_1m_pct: finiteNumber(row.anchor_performance_1m) ? row.anchor_performance_1m * 100 : null,
        anchor_performance_3m_pct: finiteNumber(row.anchor_performance_3m) ? row.anchor_performance_3m * 100 : null,
        return5_pct: valueAt(row, "return5") === null || valueAt(row, "return5") === undefined ? null : valueAt(row, "return5") * 100,
        excess5_pp:
          valueAt(row, "excess5") === null || valueAt(row, "excess5") === undefined
            ? null
            : valueAt(row, "excess5") * 100,
        theme_id: row.theme_id,
        selection_slot: row.selection_slot,
        selection_queue: row.selection_queue,
        ticker: row.ticker,
        company: row.company,
        exchange: row.exchange,
        membership_tag: row.membership_tag,
        membership_rationale: row.membership_rationale,
        above_ema21:
          row.price_close != null && row.ema21 != null
            ? row.price_close > row.ema21
            : null,
        above_ema50:
          row.price_close != null && row.ema50 != null
            ? row.price_close > row.ema50
            : null,
        ema21: row.ema21,
        ema50: row.ema50,
        adv30_usd: row.adv30_usd,
        return21_pct: valueAt(row, "return21") === null || valueAt(row, "return21") === undefined ? null : valueAt(row, "return21") * 100,
        return63_pct: valueAt(row, "return63") === null || valueAt(row, "return63") === undefined ? null : valueAt(row, "return63") * 100,
        excess21_pp:
          valueAt(row, "excess21") === null ||
          valueAt(row, "excess21") === undefined
            ? null
            : valueAt(row, "excess21") * 100,
        excess63_pp:
          valueAt(row, "excess63") === null ||
          valueAt(row, "excess63") === undefined
            ? null
            : valueAt(row, "excess63") * 100,
        relative_state: row.relative_state,
        price_trend: row.trend,
        chart_url: row.chart_url,
      };
      lines.push(
        columns
          .map(function (key) {
            return csvEscape(values[key]);
          })
          .join(","),
      );
    });
    return lines.join("\r\n");
  }

  function tradingViewExport(rows) {
    var seen = new Set();
    var symbols = [];
    var omitted = 0;
    var duplicates = 0;
    rows.forEach(function (row) {
      var key = row.tradingview_symbol;
      if (!key) throw new Error("TradingView identifier unresolved: " + row.ticker);
      if (seen.has(key)) {
        duplicates += 1;
        return;
      }
      seen.add(key);
      symbols.push(key);
    });
    return {
      text: symbols.join(",") + (symbols.length ? "\n" : ""),
      count: symbols.length,
      omitted: omitted,
      duplicates: duplicates,
    };
  }

  function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function ranked(rows, key, direction) {
    var sorted = sortRows(rows, key, direction),
      last,
      rank;
    return sorted.map(function (row, i) {
      var n = valueAt(row, key),
        valid = n !== null && n !== undefined && Number.isFinite(Number(n));
      if (valid && n !== last) rank = i + 1;
      last = n;
      return Object.assign({}, row, { display_rank: valid ? rank : null });
    });
  }
  function init(data) {
    if (document.documentElement.dataset.themescopeInitialized) return;
    document.documentElement.dataset.themescopeInitialized = "true";
    var $ = function (id) {
        return document.getElementById(id);
      },
      esc = escapeHtml;
    var finite = function (n) {
      return typeof n === "number" && Number.isFinite(n);
    };
    data.context = Array.isArray(data.context) ? data.context : [];
    data.themes = Array.isArray(data.themes) ? data.themes : [];
    data.volatility_context = Array.isArray(data.volatility_context) ? data.volatility_context : [];
    var missing =
      '<span title="Input unavailable; see diagnostic export">N/A</span>';
    var scoreConfig = data.score_methodology || {};
    var scoreBands = resolvedScoreBands(data.ui_configuration?.score_bands);
    var finalWeights = scoreConfig.theme_score_weights || {};
    var weightText = function (part, key) {
      var value = part[key];
      return typeof value === "number" ? (value * 100).toFixed(0) + "%" : "unavailable";
    };
    var currentWeight = weightText(finalWeights, "current_strength");
    var mediumWeight = weightText(finalWeights, "medium_strength");

    var infoText = {
      daily_change: "TradingView one-day price change percentage for the anchor ETF.",
      priority: "Market direction, Theme Score and valid ETF EMA inputs determine Priority. Full and Selective markets use identical rules. Research policies, not entry signals.",
      theme_score: currentWeight + " Current plus " + mediumWeight + " Medium. The color represents a relative score band, not a Long or Short signal.",
      current_strength_score: "The ETF's TradingView 1-month Performance, converted to an ascending average-rank percentile among the same eligible ETF set used for Medium.",
      medium_strength_score: "The ETF's TradingView 3-month Performance, converted to an ascending average-rank percentile among the same eligible ETF set used for Current.",
      theme_breadth21_pct: "The percentage of configured theme-watchlist stocks trading above EMA21. It does not affect Theme Score or Priority.",
      theme_breadth50_pct: "The percentage of configured theme-watchlist stocks trading above EMA50. It does not affect Theme Score or Priority.",
      rank_change_daily: "Previous-session canonical rank minus current rank. Compare only the immediately preceding US session with identical eligible universe, anchors and ranking configuration. Comparison session: " + (data.local_history?.comparison_session || "N/A") + ". " + (data.local_history?.status || "No comparable history."),
      rank_current: "The global rank of this ETF exposure by Theme Score among eligible exposures. Equal Theme Scores receive average ranks. Breadth and stock drilldown do not affect rank."
    };
    var infoCounter = 0;
    var infoTooltip = document.createElement("div");
    infoTooltip.id = "themescope-tooltip";
    infoTooltip.className = "info-tooltip";
    infoTooltip.setAttribute("role", "tooltip");
    infoTooltip.setAttribute("aria-hidden", "true");
    document.body.appendChild(infoTooltip);
    var activeInfoButton = null;
    var infoPinned = false;
    function positionInfoTooltip() {
      if (!activeInfoButton || !infoTooltip.classList.contains("is-visible")) return;
      var buttonRect = activeInfoButton.getBoundingClientRect();
      if (buttonRect.bottom < 0 || buttonRect.top > window.innerHeight || buttonRect.right < 0 || buttonRect.left > window.innerWidth) {
        closeInfoTooltip();
        return;
      }
      var tipRect = infoTooltip.getBoundingClientRect();
      var gap = 7, edge = 8;
      var below = window.innerHeight - buttonRect.bottom - edge;
      var top = below >= tipRect.height + gap || buttonRect.top < tipRect.height + gap + edge
        ? buttonRect.bottom + gap
        : buttonRect.top - tipRect.height - gap;
      var left = buttonRect.left;
      left = Math.max(edge, Math.min(left, window.innerWidth - tipRect.width - edge));
      top = Math.max(edge, Math.min(top, window.innerHeight - tipRect.height - edge));
      infoTooltip.style.left = Math.round(left) + "px";
      infoTooltip.style.top = Math.round(top) + "px";
    }
    function openInfoTooltip(button, pinned) {
      if (activeInfoButton && activeInfoButton !== button) {
        activeInfoButton.removeAttribute("aria-describedby");
        activeInfoButton.setAttribute("aria-expanded", "false");
      }
      activeInfoButton = button;
      infoPinned = Boolean(pinned);
      infoTooltip.textContent = button.dataset.tipText || "Methodology explanation unavailable.";
      infoTooltip.setAttribute("aria-hidden", "false");
      button.setAttribute("aria-describedby", infoTooltip.id);
      button.setAttribute("aria-expanded", "true");
      infoTooltip.classList.add("is-visible");
      positionInfoTooltip();
    }
    function closeInfoTooltip() {
      if (activeInfoButton) {
        activeInfoButton.removeAttribute("aria-describedby");
        activeInfoButton.setAttribute("aria-expanded", "false");
      }
      activeInfoButton = null;
      infoPinned = false;
      infoTooltip.classList.remove("is-visible");
      infoTooltip.setAttribute("aria-hidden", "true");
    }
    function customInfo(description, label) {
      return '<button type="button" class="info-button" data-tip-text="' + esc(description) + '" aria-label="' + esc(label) + '" aria-expanded="false">i</button>';
    }
    function infoControl(key) {
      var labels = {rank_current:"Current rank",theme_score:"Theme Score",current_strength_score:"Current",medium_strength_score:"Medium",excess21:"1M versus SPY",excess63:"3M versus SPY",theme_breadth21_pct:"Above EMA21",theme_breadth50_pct:"Above EMA50"};
      var description = infoText[key] || LABELS[key]?.definition || "Methodology explanation unavailable.";
      var id = "themescope-info-" + key + "-" + (++infoCounter);
      return '<span class="info-control"><button class="info-button" type="button" id="' + id + '" data-tip-text="' + esc(description) + '" aria-label="Explain ' + esc(labels[key] || LABELS[key]?.label || key) + '" aria-expanded="false">i</button></span>';
    }
    document.addEventListener("pointerover", function (event) {
      var button = event.target.closest?.(".info-button");
      if (button && button !== activeInfoButton) openInfoTooltip(button, false);
    });
    document.addEventListener("pointerout", function (event) {
      var button = event.target.closest?.(".info-button");
      if (button && button === activeInfoButton && !button.contains(event.relatedTarget) && !infoPinned) closeInfoTooltip();
    });
    document.addEventListener("focusin", function (event) {
      var button = event.target.closest?.(".info-button");
      if (button) openInfoTooltip(button, false);
    });
    document.addEventListener("focusout", function (event) {
      var button = event.target.closest?.(".info-button");
      if (button && button === activeInfoButton && !button.contains(event.relatedTarget)) closeInfoTooltip();
    });
    document.addEventListener("click", function (event) {
      var button = event.target.closest?.(".info-button");
      if (button) {
        event.preventDefault();
        if (activeInfoButton === button && infoPinned) closeInfoTooltip();
        else openInfoTooltip(button, true);
      } else if (!event.target.closest?.(".info-tooltip")) closeInfoTooltip();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && activeInfoButton) {
        closeInfoTooltip();
        activeInfoButton = null;
      }
    });
    document.addEventListener("scroll", positionInfoTooltip, true);
    window.addEventListener("resize", positionInfoTooltip);
    function pct(n, pp, reason) {
      return finite(n)
        ? '<span class="' +
            (n > 0 ? "positive" : n < 0 ? "negative" : "") +
            '">' +
            (n > 0 ? "+" : "") +
            (100 * n).toFixed(2) +
            (pp ? " pp" : "%") +
            "</span>"
        : '<span title="' +
            esc(reason || "Input unavailable; see diagnostic export") +
            '">N/A</span>';
    }
    function score(row, key) {
      const value = row[key];
      const bandClass = scoreBandClass(value, scoreBands);
      const label = finite(value) ? value.toFixed(1) : "N/A";
      return '<span class="score-chip ' + esc(bandClass) + '" aria-label="' + esc(finite(value) ? label + " score" : "Score unavailable") + '">' + label + '</span>';
    }
    function breadthUnavailableShort(metric) {
      if (!metric) return "Unavailable";
      if (metric.reason_code === "not_configured") return "Not configured";
      if (metric.reason_code === "retrieval_failed") return "Unavailable this run";
      if (metric.reason_code === "price_coverage_low") return "Fewer than 80% valid";
      if (metric.reason_code === "too_few_valid_members") return "Fewer than 8 valid members";
      return metric.reason || "Unavailable";
    }
    function marketBreadth(row, period) {
      const m = row.index_breadth?.[String(period)];
      const title = (row.ticker === "IWM" ? "Russell 2000 exported universe" : "Exported constituents") + " above EMA" + period;
      const staleLine = row.index_breadth_stale
        ? '<small class="breadth-stale" title="Price data are ' + esc(row.price_session_date || "current") + '; breadth is from an earlier observation.">Stale breadth · as of ' + esc(row.index_breadth_observation_date || "date unavailable") + '</small>'
        : '';
      if (!m || !finite(m.value) || m.status !== "valid") {
        const count = m && finite(m.valid_count) && finite(m.eligible_count) ? m.valid_count.toLocaleString("en-US") + "/" + m.eligible_count.toLocaleString("en-US") + " mapped" : "Counts unavailable";
        const reason = m?.reason || "Price history unavailable";
        const shortReason = breadthUnavailableShort(m);
        const diagnostic = "Breadth unavailable · " + count + " · " + reason;
        return '<div class="indicator-box"><div class="indicator-label">' + title + '</div><div class="breadth-unavailable" title="' + esc(diagnostic) + '"><b>Breadth unavailable</b><small>' + esc(count) + '</small><small class="breadth-reason">' + esc(shortReason) + '</small></div></div>';
      }
      const thresholdClass = breadthThresholdClass(m.value);
      const thresholdLabel = m.value.toFixed(1) + " percent, " + (m.value >= 50 ? "at or above" : "below") + " the 50 percent threshold";
      return '<div class="indicator-box"><div class="indicator-label">' + title + '</div><div class="breadth-row"><b class="breadth-value ' + thresholdClass + '" aria-label="' + esc(thresholdLabel) + '">' + m.value.toFixed(1) + '%</b><span class="breadth-count">' + m.above_count.toLocaleString("en-US") + '/' + m.valid_count.toLocaleString("en-US") + '</span></div><div class="meter"><i class="' + thresholdClass + '" style="width:' + Math.max(0, Math.min(100, m.value)) + '%"></i></div>' + staleLine + '</div>';
    }
    function conditionCard(row, period) {
      const movingAverage = row["ema" + period];
      const close = row.price_close;
      const distance = row["price_vs_ema" + period + "_pct"];
      const relationship = finite(close) && finite(movingAverage) ? close > movingAverage ? "Above" : close < movingAverage ? "Below" : "At" : "Unavailable";
      const color = relationship === "Above" ? "positive" : relationship === "Below" ? "negative" : "muted";
      return '<div class="condition-box"><small>Price vs EMA' + period + '</small><b class="ema-fact ' + color + '">' + relationship + '</b><span class="coverage-line">' + money(close) + ' vs ' + (finite(movingAverage) ? money(movingAverage) : "EMA unavailable") + ' · ' + (finite(distance) ? (distance > 0 ? "+" : "") + distance.toFixed(1) + "%" : "distance unavailable") + '</span></div>';
    }
    function ema(row, period) {
      var label=emaRelationship(row.price_close,row['ema'+period]);
      return '<span class="'+(label==='Above'?'positive':label==='Below'?'negative':'muted')+'">'+label+'</span>';
    }
    function conditions(row) {
      const breadthTitle = row.ticker === "IWM" ? "Russell 2000 Breadth" : row.ticker + " Breadth";
      const trendTitle = "ETF Price vs EMA";
      return '<section class="market-section"><h3 class="market-section-title">' + breadthTitle + '</h3><div class="market-indicators">' + marketBreadth(row, 21) + marketBreadth(row, 50) + '</div></section>' +
        '<section class="market-section"><h3 class="market-section-title">' + trendTitle + '</h3><div class="condition-row">' + conditionCard(row, 21) + conditionCard(row, 50) + '</div></section>';
    }
    function money(n, compact) {
      return finite(n)
        ? "$" +
            (compact && n >= 1e9
              ? (n / 1e9).toFixed(2) + "B"
              : compact && n >= 1e6
                ? (n / 1e6).toFixed(1) + "M"
                : n.toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  }))
        : missing;
    }
    function trend(r) {
      return r.trend_status !== "valid"
        ? '<span title="' +
            esc(r.trend_reason || "Insufficient price history") +
            '">N/A</span>'
        : '<span class="badge ' +
            (r.trend === "Uptrend"
              ? "positive"
              : r.trend === "Downtrend"
                ? "negative"
                : "") +
            '" title="Uptrend: price > EMA21 > EMA50 and EMA21 rising over 5 sessions. Downtrend: all reversed. Otherwise Mixed.">' +
            esc(r.trend) +
            "</span>";
    }
    function spark(history, key, label) {
      key = key || "close";
      label = label || "Retrieved price series";
      const rows = history || [];
      const values = rows.filter((row) => finite(row[key]));
      if (values.length < 2) return missing;
      const lo = Math.min(...values.map((row) => row[key]));
      const hi = Math.max(...values.map((row) => row[key]));
      const span = hi - lo || 1;
      const segments = [];
      let current = [];
      rows.forEach(function (row, i) {
        if (!finite(row[key])) {
          if (current.length) segments.push(current.join(" "));
          current = [];
        } else {
          current.push(((i / Math.max(1, rows.length - 1)) * 108 + 1).toFixed(1) + "," + (32 - ((row[key] - lo) / span) * 30).toFixed(1));
        }
      });
      if (current.length) segments.push(current.join(" "));
      return '<svg class="spark" viewBox="0 0 110 34" role="img" aria-label="' + esc(label) + '"><title>' + esc(values[0].date + " to " + values[values.length - 1].date) + '</title>' + segments.map((points) => '<polyline points="' + points + '" fill="none" stroke="currentColor" stroke-width="1.5"/>').join("") + '</svg>';
    }
    function directionIcon(direction) {
      if (direction !== "up" && direction !== "down") return "";
      const path = direction === "up" ? "M8 13V3M4.5 6.5 8 3l3.5 3.5" : "M8 3v10M4.5 9.5 8 13l3.5-3.5";
      return '<svg class="direction-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="' + path + '"/></svg>';
    }
    function vixChange(label, value, direction, reason) {
      return '<span><small>' + label + '</small><b class="vix-direction" title="' + esc(reason || "Change in VIX level") + '">' + pct(value, false, reason) + directionIcon(direction) + '</b></span>';
    }
    var mode = "dark";
    try {
      mode = localStorage.getItem("themescope-mode") || "dark";
    } catch (e) {}
    function setMode() {
      document.documentElement.dataset.mode = mode;
      $("mode").textContent = mode === "dark" ? "Light mode" : "Dark mode";
    }
    setMode();
    $("mode").onclick = function () {
      mode = mode === "dark" ? "light" : "dark";
      setMode();
      try {
        localStorage.setItem("themescope-mode", mode);
      } catch (e) {}
    };
    var pageIds = ["market", "daily-plan", "sectors-themes", "watchlist"];
    var initialTheme = data.themes.find((t) => (t.selected || []).length) || data.themes[0];
    var viewState = {
      theme: initialTheme?.id, themeKey: "theme_score", themeDir: "desc",
      stockKey: "excess21_pp", stockDir: "desc", themeType: "All", themePriority: "All",
      stockView: "relative", rsFilter: "All", stockSorts: {},
      page: location.hash.slice(1) || "market", themeNavigationOrder: null
    };
    if (history.state?.themescope && history.state.view?.ui_schema === 4 && history.state.view.session_date === data.session_date) {
      var firstView = history.state.view;
      viewState.theme = firstView.selected_theme_id || viewState.theme;
      viewState.themeSearch = firstView.theme_search || "";
      viewState.themeType = firstView.theme_type_filter || "All";
      viewState.themePriority = firstView.theme_priority_filter || "All";
      viewState.themeKey = firstView.theme_sort_key || viewState.themeKey;
      viewState.themeDir = firstView.theme_sort_direction || viewState.themeDir;
      viewState.stockSearch = firstView.stock_search || "";
      viewState.stockEmaFilter = firstView.stock_ema_filter || "all";
      viewState.stockKey = firstView.stock_sort_key || viewState.stockKey;
      viewState.stockDir = firstView.stock_sort_direction || viewState.stockDir;
      viewState.navigationQuery = firstView.navigation_query || "";
      viewState.themeNavigationOrder = firstView.theme_navigation_order || null;
      viewState.dailyMethodologyOpen = Boolean(firstView.daily_methodology_open);
      viewState.page = firstView.page || viewState.page;
      restoreNewView(firstView);
    }
    function restoreNewView(view) {
      viewState.stockView=view.stock_view || "relative"; viewState.rsFilter=view.rs_filter || "All"; viewState.stockSorts=view.stock_sorts || {};
    }
    var routeCache={};
    var storageKey="themescope-terminal-v4:"+data.session_date;
    try {var stored=JSON.parse(sessionStorage.getItem(storageKey));if(stored && stored.schema===4 && stored.session===data.session_date && stored.routes && typeof stored.routes==='object' && !Array.isArray(stored.routes))routeCache=stored.routes;}catch(error){}
    var displayedKey=null;
    try {history.scrollRestoration="manual";}catch(error){}
    function routeKey(){return viewState.page==='watchlist'?'watchlist:'+viewState.theme+':'+viewState.stockView:viewState.page;}
    function readRoute(){
      return {y:window.scrollY,tables:Array.from(document.querySelectorAll('#'+viewState.page+' .table-wrap')).map(function(e,i){return {index:i,x:e.scrollLeft,y:e.scrollTop};}),search:$("stock-search")?.value || "",ema:$("ema-filter")?.value || "all",rsFilter:viewState.rsFilter,key:viewState.stockKey,dir:viewState.stockDir};
    }
    function saveRoute(){
      if(!displayedKey)return;
      routeCache[displayedKey]=readRoute();
      try{sessionStorage.setItem(storageKey,JSON.stringify({schema:4,session:data.session_date,routes:routeCache}));}catch(error){}
    }
    function restoreRoute(override, options){
      displayedKey=routeKey();var saved=override || routeCache[displayedKey];
      if(override)routeCache[displayedKey]=override;
      if(viewState.page==='watchlist'){
        var sort=viewState.stockSorts[viewState.stockView] || {key:viewState.stockView==='relative'?"excess21_pp":"return21",dir:"desc"};
        viewState.stockSearch=typeof saved?.search==='string'?saved.search:"";viewState.stockEmaFilter=typeof saved?.ema==='string'?saved.ema:"all";
        viewState.stockKey=typeof saved?.key==='string'?saved.key:sort.key;viewState.stockDir=(saved?.dir || sort.dir)==='asc'?'asc':'desc';
        viewState.rsFilter=typeof saved?.rsFilter==='string'?saved.rsFilter:"All";
        $("stock-search").value=viewState.stockSearch;$("ema-filter").value=viewState.stockEmaFilter;$("rs-filter").value=viewState.rsFilter;render();
      }
      if(options?.skipScroll)return;
      document.querySelectorAll('#'+viewState.page+' .table-wrap').forEach(function(e,i){var t=Array.isArray(saved?.tables)?saved.tables.find(function(t){return t && t.index===i;}):null;e.scrollLeft=Number.isFinite(t?.x)?Math.max(0,t.x):0;e.scrollTop=Number.isFinite(t?.y)?Math.max(0,t.y):0;});
      var y=Number.isFinite(saved?.y)?saved.y:0;window.scrollTo(0,Math.max(0,Math.min(y,document.documentElement.scrollHeight-window.innerHeight)));
    }
    function captureView() {
      if ($("theme-search")) viewState.themeSearch = $("theme-search").value;
      if ($("theme-type")) viewState.themeType = $("theme-type").value;
      if ($("theme-sort")?.value) viewState.themeKey = $("theme-sort").value;
      if ($("stock-search")) viewState.stockSearch = $("stock-search").value;
      if ($("ema-filter")) viewState.stockEmaFilter = $("ema-filter").value;
      if ($("stock-sort")?.value) viewState.stockKey = $("stock-sort").value;
      if ($("watchlist-theme-search")) viewState.navigationQuery = $("watchlist-theme-search").value;
      if ($("daily-methodology")) viewState.dailyMethodologyOpen = $("daily-methodology").open;
      viewState.stockSorts[viewState.stockView]={key:viewState.stockKey,dir:viewState.stockDir};
      viewState.scroll_position = window.scrollY || 0;
      return {
        ui_schema:4,session_date:data.session_date,route_state:readRoute(),stock_view:viewState.stockView,rs_filter:viewState.rsFilter,stock_sorts:viewState.stockSorts,
        page: viewState.page, selected_theme_id: viewState.theme,
        theme_search: viewState.themeSearch || "", theme_type_filter: viewState.themeType,
        theme_priority_filter: viewState.themePriority, theme_sort_key: viewState.themeKey,
        theme_sort_direction: viewState.themeDir, stock_search: viewState.stockSearch || "",
        stock_ema_filter: viewState.stockEmaFilter || "all", stock_sort_key: viewState.stockKey,
        stock_sort_direction: viewState.stockDir,
        navigation_query: viewState.navigationQuery || "",
        theme_navigation_order: viewState.themeNavigationOrder,
        daily_methodology_open: Boolean(viewState.dailyMethodologyOpen),
        scroll_position: viewState.scroll_position
      };
    }
    function replaceHistoryState() {
      var current = history.state;
      if (current && current.themescope) {
        try { history.replaceState({ themescope: true, index: current.index, view: captureView() }, "", "#" + viewState.page); } catch (e) {}
      }
    }
    function updateBackControl() {
      var current = history.state;
      $("app-back").disabled = !(current && current.themescope && current.index > 0);
    }
    function showPage(id, navigation) {
      navigation = navigation || {};
      if (!pageIds.includes(id)) id = "market";
      if (navigation.push) {
        saveRoute();replaceHistoryState();
        if(navigation.theme)viewState.theme=navigation.theme;
        if(navigation.themeOrder)viewState.themeNavigationOrder=navigation.themeOrder;
        var view = captureView();
        view.page = id;
        var previous = history.state;
        var index = previous && previous.themescope ? previous.index + 1 : 1;
        try { history.pushState({ themescope: true, index: index, view: view }, "", "#" + id); } catch (e) {}
      }
      viewState.page = id;
      closeInfoTooltip();closeNavigation();$("navigation-status").textContent="";
      document.querySelectorAll(".page").forEach(function (page) {
        page.hidden = page.id !== id;
      });
      document.querySelectorAll(".side-nav [data-page]").forEach(function (link) {
        link.title = link.textContent.trim();
        var active = link.dataset.page === id;
        link.classList.toggle("active", active);
        if (active) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
      updateBackControl();
      if(navigation.scroll !== false)restoreRoute(null,{skipScroll:Boolean(navigation.stockTarget)});
      if(navigation.push)replaceHistoryState();
    }
    document.querySelectorAll(".side-nav [data-page]").forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        if (link.dataset.page !== viewState.page) showPage(link.dataset.page, { push: true });
      });
    });
    $("app-back").addEventListener("click", function () {
      if (!this.disabled && history.state?.themescope && history.state.index > 0) history.back();
    });
    window.addEventListener("popstate", function (event) {
      saveRoute();
      var view = event.state?.themescope && event.state.view?.ui_schema===4 && event.state.view.session_date===data.session_date ? event.state.view : null;
      if (!view) { updateBackControl(); return; }
      restoreNewView(view);
      viewState.page = view.page || "market";
      viewState.theme = view.selected_theme_id || viewState.theme;
      viewState.themeSearch = view.theme_search || ""; viewState.themeType = view.theme_type_filter || "All";
      viewState.themePriority = view.theme_priority_filter || "All"; viewState.themeKey = view.theme_sort_key || "theme_score";
      viewState.themeDir = view.theme_sort_direction || "desc"; viewState.stockSearch = view.stock_search || "";
      viewState.stockDir = view.stock_sort_direction || "desc";
      viewState.stockEmaFilter = view.stock_ema_filter || "all"; viewState.stockKey = view.stock_sort_key || "return21";
      viewState.navigationQuery = view.navigation_query || ""; viewState.themeNavigationOrder = view.theme_navigation_order || null;
      viewState.dailyMethodologyOpen = Boolean(view.daily_methodology_open);
      viewState.scroll_position = view.scroll_position || 0;
      var fields = {"theme-search":"themeSearch","theme-type":"themeType","theme-priority":"themePriority","theme-sort":"themeKey","stock-search":"stockSearch","ema-filter":"stockEmaFilter","stock-sort":"stockKey","watchlist-theme-search":"navigationQuery"};
      Object.keys(fields).forEach(function (id) { if ($(id) && viewState[fields[id]] !== undefined) $(id).value = viewState[fields[id]]; });
      $("stock-view").value=viewState.stockView; $("rs-filter").value=viewState.rsFilter;
      render(); renderDailyPlan();
      $("daily-methodology").open = viewState.dailyMethodologyOpen;
      showPage(viewState.page, { scroll: false });
      restoreRoute(view.route_state);
    });
    function sessionDisplay(value) {
      if (!value) return "Unavailable";
      const stamp = new Date(value + "T00:00:00Z");
      return Number.isNaN(stamp.valueOf()) ? value : new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(stamp);
    }
    $("date").textContent = sessionDisplay(data.session_date);
    $("sidebar-date").textContent = sessionDisplay(data.session_date);
    $("generated-hkt").textContent = data.dashboard_generated_at_hkt_display || "Unavailable";
    if (!data.session_date || !["SPY", "QQQ"].every((ticker) => (data.context || []).some((row) => row.ticker === ticker && finite(row.price_close)))) {
      const issue = data.source_status?.prices?.unavailable_reason || data.sources?.source_errors?.charts?.SPY || data.sources?.source_errors?.charts?.QQQ || "Required dated SPY/QQQ prices are missing.";
      $("status").textContent = "Market data unavailable: " + issue;
      document.querySelectorAll("section.page").forEach((section) => (section.hidden = true));
      return;
    }
    showPage(viewState.page, { scroll: false });
    var decision = data.decision || data.market_classification?.decision || {};
    var classification = data.market_classification || {};
    function themeById(id) { return data.themes.find(function (row) { return row.id === id; }); }
    function dailyThemeLink(row) {
      return '<li><a class="priority-theme-link" href="#watchlist" data-daily-theme="' + esc(row.id) + '"><b>' + esc(row.anchor+' · '+row.name) + '</b><small>' + esc(row.research_priority.label) + '</small><span>' + score(row,"theme_score") + '</span></a></li>';
    }
    function researchDownloads() {
      var research=data.daily_primary_research || {};
      if (!research.combined_file) return '<p class="muted">No directional Primary research list was generated for this session.</p>';
      return '<div class="exports">'+[[research.combined_file,"Research: Daily Primary TXT"],[research.archive_file,"Primary-filtered theme TXT ZIP"],[research.relationships_file,"Qualifying theme relationships CSV"]].map(function(item){return '<a class="download-link" download href="'+esc(item[0])+'">'+item[1]+'</a>';}).join('')+'</div><p class="caption">Anchor first in each filtered theme file. Stocks qualify by weighted stock-minus-ETF performance; the combined list deduplicates identifiers. Separate from complete data collection.</p>';
    }
    function renderMethodology() {
      var marketRows=(decision.market_matrix || []).map(function(cell){
        var active=decision.spy_price_state===cell.spy && decision.qqq_price_state===cell.qqq && decision.breadth_consensus===cell.breadth;
        return '<tr'+(active?' class="active-cell"':'')+'><td>'+esc(cell.spy || 'Unavailable')+'</td><td>'+esc(cell.qqq || 'Unavailable')+'</td><td>'+esc(cell.breadth || 'Unavailable')+'</td><td>'+esc(cell.direction)+'</td></tr>';
      }).join('');
      var policy=decision.priority_policy || {};
      $("methodology-content").innerHTML='<h3>Scores and ranks</h3><p>'+esc(infoText.current_strength_score)+'</p><p>'+esc(infoText.medium_strength_score)+'</p><p>'+esc(infoText.theme_score)+'</p><p>'+esc(infoText.rank_current)+'</p><h3>Priority policy</h3><p><b>Long bias / Selective long:</b> '+esc(policy.long_rule)+'</p><p><b>Short bias / Selective short:</b> '+esc(policy.short_rule)+'</p><p>Neutral / Unclassified: Watch for every theme.</p><p>'+esc(policy.transition_rule)+'</p><p>Priority Change compares compatible immediately preceding sessions. New long / New short includes a direction switch; Removed means Primary became Watch. N/A means no comparable priority history. This is a workflow change, not a confirmed EMA breakdown.</p><p>'+esc(policy.stock_rule)+'</p><p>'+esc(policy.note)+'</p><h3>Complete Market matrix</h3><p>Consensus is between SPY and QQQ breadth classifications, not merged constituents. IWM is context only. Unavailable evidence is never Mixed or Neutral. Unanimous price direction is retained regardless of breadth.</p><div class="table-wrap"><table><thead><tr><th>SPY Price</th><th>QQQ Price</th><th>SPY/QQQ Breadth Consensus</th><th>Result</th></tr></thead><tbody>'+marketRows+'</tbody></table></div>';
    }
    function renderDailyPlan() {
      $("daily-session").textContent=sessionDisplay(decision.session_date || data.session_date);
      $("daily-generated").textContent=data.dashboard_generated_at_hkt_display || decision.generated_at_hkt || "Unavailable";
      $("daily-classification").className="decision-tag "+directionClass(decision.market_classification);
      $("daily-classification").textContent=decision.market_classification || "Unclassified";
      $("daily-action").textContent=decision.action_sentence || "Required inputs unavailable.";
      var rows=[["SPY Price",decision.spy_price_state,"Directional input"],["QQQ Price",decision.qqq_price_state,"Directional input"],["SPY/QQQ Breadth Consensus",decision.breadth_consensus,"Consensus of two index classifications"],["Breadth qualifier",decision.breadth_qualifier,"Context for unanimous price direction"],["IWM Price",decision.iwm_price_state,"Context only, no vote"],["Russell 2000 Breadth",decision.russell_2000_breadth_state,"Context only, no vote"]];
      if(!decision.breadth_qualifier)rows=rows.filter(function(r){return r[0]!=="Breadth qualifier";});
      $("decision-path").innerHTML='<div class="decision-row header"><span>Input</span><span>Current reading</span><span>Decision role</span></div>'+rows.map(function(r){return '<div class="decision-row"><span>'+esc(r[0])+'</span><span class="'+statusClass(r[1])+'">'+esc(r[1] || 'Unavailable')+'</span><span>'+esc(r[2])+'</span></div>';}).join('');
      $("why-result").textContent=decision.reason || "Required inputs unavailable.";
      var labels={new:"New Primary Today",continuing:"Continuing Primary",unavailable:"Comparison unavailable"};
      $("daily-priorities").innerHTML=Object.keys(labels).map(function(key){
        var themes=(decision.primary_groups?.[key] || []).map(themeById).filter(Boolean);
        return '<article class="priority-card" data-priority-group="'+key+'"><h3>'+labels[key]+'</h3><p class="caption">'+themes.length+' themes</p>'+(themes.length?'<ul class="priority-theme-list">'+themes.map(dailyThemeLink).join('')+'</ul>':'<p class="muted">None today</p>')+'</article>';
      }).join('');
      $("qualification-summary").innerHTML=researchDownloads();
      $("divergence-context").textContent=decision.breadth_qualifier?'Breadth context: '+decision.breadth_qualifier+'. '+decision.reason:decision.reason;
      renderMethodology();
    }
    renderDailyPlan();
    $("daily-methodology").open = Boolean(viewState.dailyMethodologyOpen);
    $("daily-methodology").addEventListener("toggle", function () { viewState.dailyMethodologyOpen=this.open; replaceHistoryState(); });
    document.querySelectorAll("[data-page-link]").forEach(function (link) { link.addEventListener("click", function (event) { event.preventDefault(); showPage(link.dataset.pageLink, {push:true}); }); });
    $("daily-priorities").addEventListener("click", function (event) { var link=event.target.closest("[data-daily-theme]"); if (!link) return; event.preventDefault(); showPage("watchlist", {push:true,theme:link.dataset.dailyTheme}); render(); replaceHistoryState(); });
    if ($("market-direction")) {
      $("market-direction").innerHTML='<div class="market-action-card"><div><h2 class="'+directionClass(decision.market_classification)+'">'+esc(decision.market_classification)+'</h2></div><div class="market-action-details"><p>'+esc(decision.reason)+'</p><p>'+esc(decision.action_sentence)+'</p></div><button type="button" class="open-plan">Open Daily Plan</button></div>';
      $("market-direction").querySelector(".open-plan").onclick=function(){showPage("daily-plan",{push:true});};
    }
    const marketWarnings = (data.context || []).filter((row) => [21, 50].some((period) => row.index_breadth?.[String(period)]?.status !== "valid")).map((row) => row.ticker + " breadth unavailable");
    $("status").textContent = (data.run_kind === "offline_historical_diagnostic" ? "Historical diagnostic · live completeness unverified · " : "") + marketWarnings.join(" · ");
    $("cards").innerHTML = data.context.map(function(row) {
      return '<article class="market-card"><header class="market-card-head"><div><div class="market-ticker">' + esc(row.ticker) + '</div><div class="market-title-sub">' + esc({SPY:"S&P 500 ETF",QQQ:"Nasdaq-100 ETF",IWM:"Russell 2000 ETF"}[row.ticker] || row.name) + '</div></div></header><div class="market-price-row"><span class="price">' + money(row.price_close) + '</span><span class="market-daily"><small>1D</small>' + pct(row.daily_change) + '</span></div><div class="market-returns">' + [["5","1W"],["21","1M"],["63","3M"]].map(function(w){return '<span><small>' + w[1] + '</small>' + pct(row.returns[w[0]]?.value) + '</span>';}).join("") + '</div>' + conditions(row) + '</article>';
    }).join("");
    document.querySelector(".volatility-section").hidden = !(data.volatility_context || []).length;
    $("volatility-card").innerHTML = (data.volatility_context || []).map(function (item) {
      const badge = item.source_status && item.source_status !== "available" ? '<span class="source-viewState source-missing">' + esc(item.source_status) + '</span>' : '';
      const percentile = finite(item.trailing_1y_percentile) ? 'Higher than ' + item.trailing_1y_percentile.toFixed(1) + '% of observations in the last ' + item.trailing_1y_observations + ' sessions.' : '1-year percentile unavailable.';
      const summary = item.vix_direction_summary || 'Volatility direction is mixed across the displayed periods.';
      return '<article class="market-card volatility-card"><div class="market-card-head"><div><div class="market-ticker">VIX</div><div class="market-title-sub">CBOE Volatility Index</div></div>' + badge + '</div>' +
        '<div class="vix-grid"><div><div class="price">' + (finite(item.level) ? item.level.toFixed(2) : "Unavailable") + '</div><div class="market-title-sub">1-year percentile ' + (finite(item.trailing_1y_percentile) ? item.trailing_1y_percentile.toFixed(1) : "Unavailable") + '</div></div>' +
        '<div class="vix-spark">' + spark(item.history, "close", "VIX closes") + '</div><div class="market-returns">' + vixChange("Today", item.daily_change, item.vix_direction_1d, item.source_reason) + vixChange("1 week", item.return5, item.vix_direction_5d, item.source_reason) + vixChange("1 month", item.return21, item.vix_direction_21d, item.source_reason) + '</div></div>' +
        '<p class="vix-context">' + esc(percentile) + '<br>' + esc(summary) + '</p><p class="market-observation">Data ' + esc(item.observation_date || "unavailable") + (item.retrieved_at_hkt_display ? ' · Retrieved ' + esc(item.retrieved_at_hkt_display) : "") + (item.source_reason ? ' · ' + esc(item.source_reason) : "") + '</p></article>';
    }).join("");
    var metrics = {
      daily_change: "1D %",
      rank_current: "Current rank",
      rank_change_daily: "Δ Rank",
      priority: "Research priority",
      return21: "1-month Performance",
      return63: "3-month Performance",
      theme_score: "Theme Score",
      current_strength_score: "Current",
      medium_strength_score: "Medium",
      theme_breadth21_pct: "EMA21 breadth",
      theme_breadth50_pct: "EMA50 breadth",
      return5: "1-week Performance",
      price_vs_ema50_pct: "EMA50 context",
      price_close: "Price",
      adv30_usd: "Avg $Vol30",
      name: "Name",
    };
    function options(list) {
      return list.map((v) => '<option value="' + esc(v[0]) + '">' + esc(v[1]) + "</option>").join("");
    }
    function arrowIcon(direction) {
      const path = direction === "desc" ? "M8 3v10M4.5 9.5 8 13l3.5-3.5" : "M8 13V3M4.5 6.5 8 3l3.5 3.5";
      return '<svg class="direction-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="' + path + '"/></svg>';
    }
    function setDirectionButton(button, direction) {
      button.innerHTML = (direction === "desc" ? "Descending" : "Ascending") + arrowIcon(direction);
      button.classList.add("active");
      button.setAttribute("aria-pressed", "true");
    }
    function stockControls() {
      return '<label>View <select id="stock-view"><option value="performance">Performance</option><option value="relative">Relative Strength</option></select></label><label>RS ' + infoControl("rs_state") + '<select id="rs-filter"><option>All</option><option value="Outperforming">Outperforming on both 1M and 3M</option><option value="Underperforming">Underperforming on both 1M and 3M</option><option>Mixed</option><option>Missing</option></select></label><label>Search <input id="stock-search" placeholder="Ticker or company"></label>' +
        '<label>Sort by <select id="stock-sort">' + options([["return5","1W Performance"],["return21","1M Performance"],["return63","3M Performance"],["market_cap_usd","Market Cap"],["excess21_pp","1M vs ETF (pp)"],["excess63_pp","3M vs ETF (pp)"],["adv30_usd","Avg $Vol30"],["turnover_1d_usd","Turnover 1D"],["relative_volume_1d","Relative Volume"],["price_close","Price"]]) +
        '</select></label><button id="stock-direction" type="button"></button>' +
        '<label>EMA <select id="ema-filter"><option value="all">All</option><option value="above21">Above EMA21</option><option value="below21">At/below EMA21</option><option value="above50">Above EMA50</option><option value="below50">At/below EMA50</option></select></label>';
    }
    $("theme-controls").innerHTML = '<label>Search <input id="theme-search" placeholder="Sector, theme or ETF"></label>' +
      '<label>Type <select id="theme-type"><option>All</option><option>Sector</option><option>Theme</option></select></label>' +
      '<label>Research Priority <select id="theme-priority"><option value="All">All</option><option>Primary long</option><option>Watch</option><option>Primary short</option></select></label>' +
      '<label>Sort by <select id="theme-sort">' + options(Object.entries(metrics).filter(([key]) => !["price_close","adv30_usd","name"].includes(key))) + '</select></label>' +
      '<button id="theme-direction" type="button"></button>';
    $("stock-controls").innerHTML = stockControls();
    $("theme-search").value = viewState.themeSearch || "";
    $("theme-type").value = viewState.themeType;
    $("theme-priority").value = viewState.themePriority;
    $("theme-priority").onchange = function(){viewState.themePriority=this.value;render();persistView();};
    $("theme-sort").value = viewState.themeKey;
    $("stock-search").value = viewState.stockSearch || "";
    $("stock-view").value=viewState.stockView; $("rs-filter").value=viewState.rsFilter;
    $("stock-view").onchange=function(){
      saveRoute();viewState.stockSorts[viewState.stockView]={key:viewState.stockKey,dir:viewState.stockDir};viewState.stockView=this.value;
      var sort=viewState.stockSorts[viewState.stockView] || {key:viewState.stockView === "relative" ? "excess21_pp" : "return21",dir:"desc"};
      viewState.stockKey=sort.key;viewState.stockDir=sort.dir;$("stock-sort").value=sort.key;render();restoreRoute();persistView();
    };
    $("rs-filter").onchange=function(){viewState.rsFilter=this.value;render();persistView();};
    $("stock-sort").value = viewState.stockKey;
    $("ema-filter").value = viewState.stockEmaFilter || "all";
    $("watchlist-theme-search").value = viewState.navigationQuery || "";
    function persistView() { replaceHistoryState(); }
    $("theme-sort").onchange = function () { viewState.themeKey = this.value; render(); persistView(); };
    $("theme-direction").onclick = function () { viewState.themeDir = viewState.themeDir === "desc" ? "asc" : "desc"; render(); persistView(); };
    $("theme-search").addEventListener("input", function () { viewState.themeSearch = this.value; render(); persistView(); });
    $("theme-type").onchange = function () { viewState.themeType = this.value; render(); persistView(); };
    $("stock-sort").onchange = function () { viewState.stockKey = this.value; render(); persistView(); };
    $("stock-direction").onclick = function () { viewState.stockDir = viewState.stockDir === "desc" ? "asc" : "desc"; render(); persistView(); };
    $("stock-search").addEventListener("input", function () { viewState.stockSearch = this.value; render(); persistView(); });
    $("ema-filter").onchange = function () { viewState.stockEmaFilter = this.value; render(); persistView(); };

    var navigationInput=$("watchlist-theme-search"), navigationPopup=$("navigation-popup");
    var navigationIndex=buildNavigationIndex(data.themes), navigationMatches=[], navigationShown=[];
    var navigationLimits={stock:12,theme:12}, navigationActive=-1, targetTimer, navigationSuppressFocus=false;
    function closeNavigation(){
      if(!navigationInput)return;
      navigationPopup.hidden=true;navigationInput.setAttribute('aria-expanded','false');
      navigationInput.removeAttribute('aria-activedescendant');navigationActive=-1;
    }
    function positionNavigation(){
      if(!navigationInput || navigationPopup.hidden)return;
      var rect=navigationInput.getBoundingClientRect(),below=window.innerHeight-rect.bottom-16,above=rect.top-16;
      var upward=below<180 && above>below;
      navigationPopup.style.top=upward?'auto':'calc(100% + 6px)';
      navigationPopup.style.bottom=upward?'calc(100% + 6px)':'auto';
      navigationPopup.style.maxHeight=Math.max(80,Math.min(420,upward?above:below))+'px';
    }
    function revealNavigationInput(){
      var rect=navigationInput.getBoundingClientRect(),edge=document.querySelector('.topbar').getBoundingClientRect().bottom+8;
      if(rect.top<edge)window.scrollBy(0,rect.top-edge);
      else if(rect.bottom>window.innerHeight-12)window.scrollBy(0,rect.bottom-window.innerHeight+12);
    }
    function setNavigationActive(index){
      navigationActive=index;
      $("navigation-results").querySelectorAll('[role="option"]').forEach(function(option,i){option.setAttribute('aria-selected',String(i===index));});
      var option=$("navigation-option-"+index);
      if(option){navigationInput.setAttribute('aria-activedescendant',option.id);option.scrollIntoView({block:'nearest'});}
      else navigationInput.removeAttribute('aria-activedescendant');
    }
    function renderNavigation(){
      navigationMatches=searchNavigation(navigationIndex,navigationInput.value);navigationShown=[];
      if(!navigationInput.value.trim()){closeNavigation();return;}
      revealNavigationInput();
      var more=[];
      $("navigation-results").innerHTML=['stock','theme'].map(function(kind){
        var matches=navigationMatches.filter(function(r){return r.kind===kind;}),rows=matches.slice(0,navigationLimits[kind]);
        if(!matches.length)return '';
        var label=kind==='stock'?'Stocks':'Sectors & Themes';
        if(matches.length>rows.length)more.push('<button type="button" data-navigation-more="'+kind+'">Show more '+(kind==='stock'?'stocks':'themes')+' ('+(matches.length-rows.length)+' remaining)</button>');
        return '<div role="group" aria-labelledby="navigation-group-'+kind+'"><div class="navigation-group-title" id="navigation-group-'+kind+'">'+label+' · '+rows.length+' of '+matches.length+'</div>'+rows.map(function(row){
          var index=navigationShown.length;navigationShown.push(row);
          return '<div role="option" aria-selected="false" id="navigation-option-'+index+'" data-navigation-kind="'+row.kind+'" data-theme-id="'+esc(row.themeId)+'" data-symbol="'+esc(row.symbol)+'" data-navigation-index="'+index+'"><b>'+esc(row.ticker)+'</b><span>'+esc(row.kind==='stock'?row.themeName+' · '+row.anchor:row.themeName)+'</span></div>';
        }).join('')+'</div>';
      }).join('');
      $("navigation-more").innerHTML=more.join('');
      $("navigation-result-count").textContent=navigationMatches.length?navigationShown.length+' of '+navigationMatches.length+' matching results':'No matching stocks or themes.';
      navigationPopup.hidden=false;navigationInput.setAttribute('aria-expanded','true');
      navigationInput.removeAttribute('aria-activedescendant');navigationActive=-1;positionNavigation();
    }
    function chooseNavigation(result){
      if(!result)return;
      closeNavigation();
      if(result.kind==='theme'){
        showPage('watchlist',{push:true,theme:result.themeId});render();replaceHistoryState();navigationSuppressFocus=true;navigationInput.focus({preventScroll:true});navigationSuppressFocus=false;return;
      }
      showPage('watchlist',{push:true,theme:result.themeId,stockTarget:true});
      var theme=themeById(result.themeId),stock=theme.selected.find(function(r){return r.tradingview_symbol===result.symbol;}),adjusted=[];
      if(!filterRows([stock],{query:$("stock-search").value}).length){$("stock-search").value='';viewState.stockSearch='';adjusted.push('within-list search');}
      if(!emaMatches(stock,$("ema-filter").value)){$("ema-filter").value='all';viewState.stockEmaFilter='all';adjusted.push('EMA');}
      if(viewState.stockView==='relative' && !rsMatches(stock,viewState.rsFilter)){viewState.rsFilter='All';$("rs-filter").value='All';adjusted.push('RS');}
      render();
      $("navigation-status").textContent=adjusted.length?'Filters adjusted to reveal '+stock.ticker+': '+adjusted.join(', ')+'.':'';
      var row=Array.from($("stock-body").rows).find(function(r){return r.dataset.stockSymbol===result.symbol;});
      if(row){
        $("stock-table-wrap").scrollLeft=0;
        row.classList.add('navigation-target');row.focus({preventScroll:true});row.scrollIntoView({block:'center',inline:'nearest',behavior:'auto'});
        clearTimeout(targetTimer);targetTimer=setTimeout(function(){row.classList.remove('navigation-target');},1600);
      }
      saveRoute();replaceHistoryState();
    }
    navigationInput.addEventListener('input',function(){viewState.navigationQuery=this.value;navigationLimits={stock:12,theme:12};renderNavigation();persistView();});
    navigationInput.addEventListener('focus',function(){if(!navigationSuppressFocus){revealNavigationInput();if(this.value.trim())renderNavigation();}});
    navigationInput.addEventListener('keydown',function(event){
      if(event.key==='Escape'){event.preventDefault();closeNavigation();return;}
      if(event.key==='ArrowDown' || event.key==='ArrowUp'){
        event.preventDefault();if(navigationPopup.hidden)renderNavigation();
        if(navigationShown.length)setNavigationActive(event.key==='ArrowDown'?(navigationActive+1)%navigationShown.length:(navigationActive<0?navigationShown.length-1:(navigationActive-1+navigationShown.length)%navigationShown.length));
      }else if(event.key==='Enter' && !navigationPopup.hidden){event.preventDefault();chooseNavigation(navigationShown[Math.max(0,navigationActive)]);}
    });
    $("navigation-results").addEventListener('click',function(event){var option=event.target.closest('[data-navigation-index]');if(option)chooseNavigation(navigationShown[Number(option.dataset.navigationIndex)]);});
    $("navigation-more").addEventListener('click',function(event){var button=event.target.closest('[data-navigation-more]');if(button){navigationLimits[button.dataset.navigationMore]+=12;renderNavigation();navigationInput.focus({preventScroll:true});}});
    document.addEventListener('click',function(event){if(!event.composedPath().includes(document.querySelector('.navigation-search')))closeNavigation();});
    document.addEventListener('focusin',function(event){if(!event.target.closest('.navigation-search'))closeNavigation();});
    document.querySelector('.navigation-search').addEventListener('keydown',function(event){
      if(event.key==='Escape' && event.target!==navigationInput){event.preventDefault();closeNavigation();navigationSuppressFocus=true;navigationInput.focus({preventScroll:true});navigationSuppressFocus=false;}
    });
    window.addEventListener('resize',positionNavigation);

    function filtered(rows, p) {
      if (p === "theme") {
        const query = $("theme-search").value.trim().toLowerCase();
        return rows.filter(function (row) {
          const matchesText = !query || [row.name, row.anchor, row.id].some((v) => String(v || "").toLowerCase().includes(query));
          const type = row.level === "Sector" ? "Sector" : "Theme";
          const matchesType = viewState.themeType === "All" || type === viewState.themeType;
          return matchesText && matchesType && (viewState.themePriority === "All" || row.research_priority?.label === viewState.themePriority);
        });
      }
      return filterRows(rows, { query: $("stock-search").value }).filter(function(row){return viewState.stockView !== "relative" || rsMatches(row,viewState.rsFilter);}).filter(function(row){return emaMatches(row,$("ema-filter").value);});
    }

    function renderThemeSelector() {
      var sectorOptions = (data.themes || []).filter((row) => row.level === "Sector").map((row) => '<option value="' + esc(row.id) + '">' + esc(row.name) + ' · ' + esc(row.anchor) + '</option>').join("");
      var themeOptions = (data.themes || []).filter((row) => row.level !== "Sector").map((row) => '<option value="' + esc(row.id) + '">' + esc(row.name) + ' · ' + esc(row.anchor) + '</option>').join("");
      $("watchlist-theme-selector").innerHTML = '<optgroup label="Sectors">' + (sectorOptions || '<option disabled>No matching sectors</option>') + '</optgroup><optgroup label="Themes">' + (themeOptions || '<option disabled>No matching themes</option>') + '</optgroup>';
      if ((data.themes || []).some((row) => row.id === viewState.theme)) $("watchlist-theme-selector").value = viewState.theme;
    }
    function themeNavigationOrder() {
      var allIds = new Set((data.themes || []).map((row) => row.id));
      var order = (viewState.themeNavigationOrder || []).filter((id) => allIds.has(id));
      return order.length > 0 ? order : sortRows(data.themes || [], "theme_score", "desc").map((row) => row.id);
    }
    function switchTheme(id, order) {
      if (!id || id === viewState.theme) return;
      showPage("watchlist", { push: true, theme:id, themeOrder:order });
      render();
      replaceHistoryState();
    }
    $("watchlist-theme-selector").onchange = function () { switchTheme(this.value); };
    $("previous-theme").onclick = function () {
      var order = themeNavigationOrder(), index = order.indexOf(viewState.theme);
      if (index < 0) index = 0;
      if (order.length) switchTheme(order[(index - 1 + order.length) % order.length], order);
    };
    $("next-theme").onclick = function () {
      var order = themeNavigationOrder(), index = order.indexOf(viewState.theme);
      if (index < 0) index = -1;
      if (order.length) switchTheme(order[(index + 1) % order.length], order);
    };

    function head(p, columns) {
      $(p + "-head").innerHTML =
        "<tr>" +
        columns
          .map(
            (c) => {
              var fullLabel = c[4] || c[0];
              var label = c[1]
                ? '<button data-sort="' + c[1] + '" title="Sort by ' + esc(fullLabel) + '; unavailable values stay last" aria-label="Sort by ' + esc(fullLabel) + '">' + c[0] + (viewState[p + "Key"] === c[1] ? arrowIcon(viewState[p + "Dir"]) : "") + '</button>'
                : '<span title="' + esc(fullLabel) + '">' + c[0] + '</span>';
              var sortState = c[1] ? (viewState[p + "Key"] === c[1] ? (viewState[p + "Dir"] === "asc" ? "ascending" : "descending") : "none") : null;
              return '<th class="' + esc(c[5] || "") + '"' + (sortState ? ' aria-sort="' + sortState + '"' : '') + '><div class="th-content">' + label + (c[3] ? infoControl(c[3]) : '') + '</div></th>';
            },
          )
          .join("") +
        "</tr>";
      $(p + "-head")
        .querySelectorAll("button[data-sort]")
        .forEach(
          (b) =>
            (b.onclick = function () {
              var key = this.dataset.sort;
              viewState[p + "Dir"] =
                viewState[p + "Key"] === key && viewState[p + "Dir"] === "desc"
                  ? "asc"
                  : "desc";
              viewState[p + "Key"] = key;
              if ($(p + "-sort")) $(p + "-sort").value = key;
              render();
              persistView();
            }),
        );
    }
    function td(columnClass, content, extraAttributes) {
      return '<td class="' + columnClass + '"' + (extraAttributes || '') + '>' + content + '</td>';
    }
    function themeBreadthCell(row, period) {
      const metric = row.theme_watchlist_breadth?.[String(period)];
      const value = row["theme_breadth" + period + "_pct"];
      if (!metric || !finite(value) || metric.status !== "valid") {
      return '<span class="breadth-unavailable-cell" aria-label="Theme Breadth unavailable">N/A</span>';
      }
      const thresholdClass = breadthThresholdClass(value);
      return '<span class="' + thresholdClass + '" aria-label="' + value.toFixed(1) + ' percent, ' + (value >= 50 ? 'at or above' : 'below') + ' the 50 percent threshold">' + value.toFixed(1) + '%</span>';
    }
    function breadthSummary(row, period) {
      const metric = row.theme_watchlist_breadth?.[String(period)];
      if (!metric || metric.status !== "valid" || !finite(row["theme_breadth" + period + "_pct"])) {
        const count = metric && finite(metric.valid_count) && finite(metric.eligible_count) ? metric.valid_count + "/" + metric.eligible_count + " valid members" : "counts unavailable";
        return (metric?.reason || "Breadth unavailable") + " (" + count + ")";
      }
      return row["theme_breadth" + period + "_pct"].toFixed(1) + "% (" + metric.above_count + "/" + metric.valid_count + ")";
    }
    function pp(value){return finite(value) ? '<span class="'+(value>0?"positive":value<0?"negative":"muted")+'">'+(value>0?"+":"")+value.toFixed(2)+' pp</span>' : "N/A";}
    function tickerCell(row){return '<a href="'+esc(row.chart_url || "#watchlist")+'" target="_blank" rel="noopener noreferrer">'+esc(row.ticker)+'</a> '+customInfo([row.company,row.exchange,row.membership_rationale].filter(Boolean).join(" · "),"Information for "+row.ticker);}
    function earnings(value) {
      if (!value) return "N/A";
      var date = new Date(value + "T00:00:00Z");
      if (!Number.isFinite(date.valueOf())) return '<span aria-label="Earnings date ' + esc(value) + '">' + esc(value) + '</span>';
      var crossYear = String(value).slice(0,4) !== String(data.session_date).slice(0,4);
      var label = new Intl.DateTimeFormat("en-US", {month:"short",day:"numeric",timeZone:"UTC", ...(crossYear ? {year:"2-digit"} : {})}).format(date);
      return '<time datetime="' + esc(value) + '" aria-label="Earnings date ' + esc(value) + '">' + esc(label) + '</time>';
    }
    function stockDrilldownMessage(row) {
      var status = row.stock_drilldown_status;
      if (!status) status = ["complete", "reviewed_short", "reviewed_etf_only", "configured"].includes(row.watchlist_status) ? (row.watchlist_member_count ? "available" : row.watchlist_status) : "not_configured";
      if (status === "reviewed_etf_only") return "Reviewed exception: " + (row.watchlist_exception_reason || row.watchlist_unavailable_reason || "no eligible stock reasonably represents this exposure.");
      if (status === "not_configured") return "Theme watchlist not configured.";
      if (status === "retrieval_failed") return "Stock drilldown unavailable this run because the configured company list could not be retrieved.";
      return "No configured stocks are available in this watchlist.";
    }
    function select(id) {
      showPage("watchlist", { push: true, theme:id, themeOrder:visibleThemes.map((row) => row.id) });
      render();
      replaceHistoryState();
    }
    $("theme-body").addEventListener("click", function (event) {
      var row = event.target.closest("tr[data-theme]");
      if (row && !event.target.closest("a")) select(row.dataset.theme);
    });
    function renderEarnings(){
      var e=data.expected_earnings || {upcoming:[],unknown:[]};
      $("expected-earnings-content").innerHTML='<p class="caption">'+esc(e.as_of || data.session_date)+' through '+esc(e.through || "N/A")+', inclusive. Expected dates; verify before relying on them.</p>'+(e.upcoming.length?'<div class="table-wrap earnings-table-wrap"><table><thead><tr><th>Ticker</th><th>Expected date</th><th>Days away</th><th>Primary themes</th></tr></thead><tbody>'+e.upcoming.map(function(r){return '<tr><td>'+esc(r.ticker)+'</td><td>'+esc(r.expected_date)+'</td><td>'+esc(r.timing_label)+'</td><td>'+r.contexts.map(function(c){return '<a href="#watchlist" data-earnings-theme="'+esc(c.theme_id)+'">'+esc(c.theme_name+' ('+c.anchor+')')+'</a>';}).join(' · ')+'</td></tr>';}).join('')+'</tbody></table></div>':'<p>No supplied expected dates fall within this window.</p>')+'<p>'+e.unknown.length+' stocks have unknown or unavailable dates; missing does not mean no event.</p>'+(e.unknown.length?'<details><summary>Unknown / unavailable dates</summary><ul>'+e.unknown.map(function(r){return '<li>'+esc(r.ticker+': '+r.reason+(r.expected_date?' ('+r.expected_date+')':''))+' · '+r.contexts.map(function(c){return '<a href="#watchlist" data-earnings-theme="'+esc(c.theme_id)+'">'+esc(c.theme_name+' ('+c.anchor+')')+'</a>';}).join(' · ')+'</li>';}).join('')+'</ul></details>':'');
    }
    $("expected-earnings-content").addEventListener('click',function(event){var link=event.target.closest('[data-earnings-theme]');if(link){event.preventDefault();select(link.dataset.earningsTheme);}});
    renderEarnings();
    var researchFiles=(data.export_manifest || []).filter(function(f){return f.role==='individual_research';});
    $("all-individual-watchlists").hidden=!researchFiles.length;
    $("individual-export-count").textContent=researchFiles.length+' individual files · anchor first, then configured stocks. Update only when memberships or identifiers change.';
    $("daily-data-export-links").innerHTML=(data.export_manifest || []).filter(function(f){return ['configured_stock_daily_data','configured_etf_daily_data'].includes(f.role);}).map(function(f){return '<a class="download-link" download href="'+esc(f.file)+'">'+(f.role==='configured_stock_daily_data'?'Data Collection: All Configured Stocks':'Data Collection: All ETFs')+' · '+f.instrument_count+'</a>';}).join(' ');
    $("grouped-export-links").innerHTML=(data.export_manifest || []).filter(function(f){return f.role==='optional_broad_scan';}).map(function(f){return '<a class="download-link" download href="'+esc(f.file)+'">'+esc(f.group)+' · '+f.instrument_count+' unique instruments</a>';}).join(' ');
    var visible = [];
    var visibleThemes = [];
    function render() {
      closeInfoTooltip();
      var viewSortOptions=viewState.stockView === "relative" ? [["return21","Stock 1M"],["anchor_performance_1m","ETF 1M"],["excess21_pp","1M vs ETF (pp)"],["return63","Stock 3M"],["anchor_performance_3m","ETF 3M"],["excess63_pp","3M vs ETF (pp)"]] : [["return5","1W Performance"],["return21","1M Performance"],["return63","3M Performance"],["market_cap_usd","Market Cap"],["adv30_usd","Avg $Vol30"],["turnover_1d_usd","Turnover 1D"],["relative_volume_1d","Rel Vol"],["price_close","Price"]];
      if(!viewSortOptions.some(function(o){return o[0]===viewState.stockKey;}))viewState.stockKey=viewState.stockView === "relative" ? "excess21_pp" : "return21";
      $("stock-sort").innerHTML=options(viewSortOptions);$("stock-sort").value=viewState.stockKey;
      setDirectionButton($("stock-direction"), viewState.stockDir);
      setDirectionButton($("theme-direction"), viewState.themeDir);
      var all = sortRows(data.themes || [], viewState.themeKey, viewState.themeDir).map((row) => Object.assign({}, row, { display_rank: row.global_rank }));
      visibleThemes = filtered(all, "theme");
      renderThemeSelector();
      const breadthUnavailable = visibleThemes.filter((row) => row.breadth_status_21 !== "valid" || row.breadth_status_50 !== "valid").length;
      $("theme-count").textContent = visibleThemes.length + " of " + all.length + " exposures" + (breadthUnavailable ? " · " + breadthUnavailable + " with breadth unavailable" : "");
      const themeColumns = [
        ["#", "rank_current", null, "rank_current", "Current rank", "col-rank"], ["Δ Rank", "rank_change_daily", null, "rank_change_daily", "Previous-session rank minus current-session rank", "col-rank-daily"], ["Name", "name", null, null, "Sector or theme name with exposure type", "col-name"], ["ETF", null, null, null, "Anchor ETF", "col-etf"], ["1D %", "daily_change", null, "daily_change", "TradingView one-day price change percentage for the anchor ETF.", "col-day-change"],
        ["Priority", "priority", null, "priority", "Configured directional research priority; not an entry signal.", "col-priority"], ["Priority Change", "priority_change", null, null, "Workflow change since the compatible immediately preceding session; N/A without comparable history.", "col-priority-change"], ["Score", "theme_score", null, "theme_score", "Theme Score", "col-score"], ["Current", "current_strength_score", null, "current_strength_score", "1-month Performance percentile", "col-current"], ["Medium", "medium_strength_score", null, "medium_strength_score", "3-month Performance percentile", "col-medium"],
        ["1W", "return5", null, null, "TradingView 1-week Performance; context only", "col-return"], ["1M", "return21", null, null, "TradingView 1-month Performance", "col-return"], ["3M", "return63", null, null, "TradingView 3-month Performance", "col-return"], ["vs EMA21", null, null, null, "Anchor price relative to daily EMA21", "col-ema"], ["vs EMA50", null, null, null, "Anchor price relative to daily EMA50", "col-ema"],
        ["% > EMA21", "theme_breadth21_pct", null, "theme_breadth21_pct", "Available when at least eight configured members and 80 percent coverage have valid Price, EMA21 and EMA50 values. Does not affect Theme Score or Priority.", "col-breadth"], ["% > EMA50", "theme_breadth50_pct", null, "theme_breadth50_pct", "Available when at least eight configured members and 80 percent coverage have valid Price, EMA21 and EMA50 values. Does not affect Theme Score or Priority.", "col-breadth"],
      ];
      $("theme-cols").innerHTML = themeColumns.map(function (column) { return '<col class="' + column[5] + '">'; }).join("");
      head("theme", themeColumns);
      $("theme-body").innerHTML = visibleThemes.map(function (row) {
        const type = row.level === "Sector" ? "Sector" : "Theme";
        return '<tr data-theme="' + esc(row.id) + '" class="' + (row.id === viewState.theme ? "active " : "") + (priorityCategory(row) === "primary" ? "primary-row primary-" + row.research_priority.side : "") + '">' +
          td("col-rank", row.display_rank ?? "N/A") +
          td("col-rank-daily", finite(row.rank_change_daily) ? '<span class="' + (row.rank_change_daily > 0 ? "positive" : row.rank_change_daily < 0 ? "negative" : "muted") + '">' + (row.rank_change_daily > 0 ? "+" : "") + row.rank_change_daily + '</span>' : "N/A") +
          td("col-name", '<div class="theme-name-cell"><span class="type-tag">' + type + '</span><button class="theme-select" aria-label="Open watchlist for ' + esc(row.name) + '">' + esc(row.name) + '</button></div>') +
          td("col-etf", row.chart_url ? '<a href="' + esc(row.chart_url) + '" target="_blank" rel="noopener noreferrer">' + esc(row.anchor) + '</a>' : esc(row.anchor)) +
          td("col-day-change", pct(row.daily_change)) +
          td("col-priority", '<span class="'+(row.research_priority?.category==='primary'?'':'muted')+'">'+esc(row.research_priority?.label || "Watch")+'</span>') +
          td("col-priority-change", '<span class="'+(row.priority_change==='New long'?'positive':row.priority_change==='New short'?'negative':'muted')+'">'+esc(row.priority_change || "N/A")+'</span>') +
          td("col-score", score(row, "theme_score")) +
          td("col-current", score(row, "current_strength_score")) +
          td("col-medium", score(row, "medium_strength_score")) +
          td("col-return", pct(valueAt(row, "return5"))) +
          td("col-return", pct(valueAt(row, "return21"))) +
          td("col-return", pct(valueAt(row, "return63"))) +
          td("col-ema", ema(row, 21)) + td("col-ema", ema(row, 50)) +
          td("col-breadth", themeBreadthCell(row, 21)) +
          td("col-breadth", themeBreadthCell(row, 50)) + '</tr>';
      }).join("") || '<tr><td colspan="17">No eligible ETF exposures are available in this snapshot.</td></tr>';
      var selected = data.themes.find((row) => row.id === viewState.theme) || data.themes[0];
      if (!selected) {
        $("active-name").textContent = "Watchlist";
        $("active-summary").textContent = "No eligible ETF anchor is available in this snapshot.";
        $("watchlist-message").hidden = false;
        $("watchlist-message").textContent = "No eligible anchor ETF is available in this snapshot.";
        $("stock-controls").hidden = true;
        $("stock-exports").hidden = true;
        $("coverage").textContent = "";
        $("stock-table-wrap").hidden = true;
        $("csv").disabled = true;
        $("tv").hidden = true;
        return;
      }
      $("csv").disabled = false;
      var individualExport=(data.export_manifest || []).find(function(item){return item.role==='individual_research' && item.theme_id===selected.id;});
      $("tv").hidden=!individualExport;
      if(individualExport){$("tv").href=individualExport.file;$("tv").download=individualExport.file.split('/').pop();}
      $("stock-exports").hidden = false;
      $("stock-controls").hidden = false;
      $("stock-table-wrap").hidden = false;
      $("watchlist-message").hidden = true;
      $("active-name").textContent = selected.name
        ? selected.name + (selected.anchor ? " / " + selected.anchor : "")
        : "Watchlist";
      $("active-summary").innerHTML = '<div class="summary-scores">' + esc(selected.research_priority?.label || "Watch") + ' · ' + score(selected, "theme_score") + ' ' + score(selected, "current_strength_score") + ' ' + score(selected, "medium_strength_score") + '</div>' +
        '<div class="summary-returns"><span>1W Performance ' + pct(valueAt(selected, "return5")) + '</span><span>1M Performance ' + pct(valueAt(selected, "return21")) + '</span><span>3M Performance ' + pct(valueAt(selected, "return63")) + '</span></div>' +
        '<div class="summary-rank">Rank ' + (selected.rank_current ?? selected.global_rank ?? "unavailable") + ' of ' + data.themes.length + '</div>' +
        '<div class="summary-breadth">Theme breadth — EMA21 ' + breadthSummary(selected, 21) + ' · EMA50 ' + breadthSummary(selected, 50) + '</div>' +
        '<div class="summary-returns"><span>Anchor EMA21 ' + ema(selected, 21) + '</span><span>Anchor EMA50 ' + ema(selected, 50) + '</span></div>';
      var primaryExport=(data.export_manifest || []).find(function(item){return item.role==='individual_primary_research' && item.theme_id===selected.id;});
      $("tv-primary").hidden=!primaryExport;
      if(primaryExport)$("tv-primary").href=primaryExport.file;else $("tv-primary").removeAttribute('href');
      var base = (selected.selected || []).slice();
      base = base.map((row) => Object.assign({}, row, { theme_id: selected.id, theme_name: selected.name, generated_at: data.dashboard_generated_at || data.generated_at }));
      visible = filtered(sortRows(base, viewState.stockKey, viewState.stockDir).map((row) => Object.assign({}, row, { display_rank: row.selection_slot })), "stock");
      var hasCuratedList = base.length > 0;
      $("stock-controls").hidden = !hasCuratedList;
      $("stock-table-wrap").hidden = !hasCuratedList;
      $("stock-exports").hidden = !hasCuratedList;
      $("watchlist-message").hidden = hasCuratedList;
      if (!hasCuratedList) {
        $("watchlist-message").textContent = stockDrilldownMessage(selected);
        $("coverage").textContent = "";
        visible = [];
        $("csv").disabled = true;

      } else {
        $("coverage").textContent = visible.length + " of " + base.length + " configured stocks";
      }
      $("rs-filter").closest("label").hidden = viewState.stockView !== "relative";
      $("stock-table-wrap").classList.toggle("relative-view",viewState.stockView === "relative");
      var stockColumns = [
        ["#",null,null,null,"Configured position","col-rank"], ["Ticker",null,null,null,"Stock ticker; information includes company, exchange and membership rationale","col-ticker"],
        ["Price","price_close",null,null,"Stock Price","col-price"], ["1D","daily_change",null,null,"TradingView one-day price change percent","col-return"], ["Market Cap","market_cap_usd",null,"market_cap_usd","Company market capitalization in USD; supplied Stock CSV value","col-cap"],
        ["1W","return5",null,null,"TradingView 1W Performance percent","col-return"], ["1M","return21",null,null,"TradingView 1M Performance percent","col-return"], ["3M","return63",null,null,"TradingView 3M Performance percent","col-return"],
        ["EMA21",null,null,null,"Stock Price vs EMA21","col-ema"], ["EMA50",null,null,null,"Stock Price vs EMA50","col-ema"],
        ["ATR%14","atr14_pct",null,"atr14_pct",LABELS.atr14_pct.definition,"col-return"], ["Avg $Vol30","adv30_usd",null,"adv30_usd",LABELS.adv30_usd.definition,"col-adv"],
        ["Turnover 1D","turnover_1d_usd",null,"turnover_1d_usd",LABELS.turnover_1d_usd.definition,"col-adv"], ["Rel Vol","relative_volume_1d",null,"relative_volume_1d",LABELS.relative_volume_1d.definition,"col-relvol"], ["Earnings",null,null,null,"Upcoming earnings; full date in accessible label","col-earnings"]
      ];
      if(viewState.stockView === "relative") stockColumns=[
        ["#",null,null,null,"Stable configured membership position; not RS rank","col-rank"],["Ticker",null,null,null,"Stock ticker","col-ticker"],["Anchor",null,null,null,"Selected anchor ETF","col-anchor"],
        ["Stock 1M","return21",null,null,"Stock TradingView 1M Performance percent","col-rs-return"],["ETF 1M","anchor_performance_1m",null,null,"Selected ETF TradingView 1M Performance percent","col-rs-return"],["1M vs ETF (pp)","excess21_pp",null,"excess21_pp","Stock minus selected ETF 1M Performance, in percentage points","col-rs-diff"],
        ["Stock 3M","return63",null,null,"Stock TradingView 3M Performance percent","col-rs-return"],["ETF 3M","anchor_performance_3m",null,null,"Selected ETF TradingView 3M Performance percent","col-rs-return"],["3M vs ETF (pp)","excess63_pp",null,"excess63_pp","Stock minus selected ETF 3M Performance, in percentage points","col-rs-diff"],
        ["EMA21",null,null,null,"Stock Price vs EMA21","col-ema"],["EMA50",null,null,null,"Stock Price vs EMA50","col-ema"],["Expected earnings",null,null,null,"Expected date; verify before relying on it","col-earnings"]];
      $("stock-cols").innerHTML = stockColumns.map(function(c){return '<col class="' + c[5] + '">';}).join("");
      head("stock", stockColumns);
      var stockColumnCount=stockColumns.length;
      $("stock-body").innerHTML = visible.map(function (row) {
        const url = row.chart_url || null;
        const rationale = row.membership_rationale || row.evidence_note || "Business relevance rationale recorded in the membership source.";
        if(viewState.stockView === "relative")return '<tr tabindex="-1" data-stock-symbol="'+esc(row.tradingview_symbol)+'">'+td("col-rank",row.selection_slot ?? "N/A")+td("col-ticker",tickerCell(row))+td("col-anchor",esc(selected.anchor))+
          td("col-rs-return",pct(valueAt(row,"return21")))+td("col-rs-return",pct(row.anchor_performance_1m))+td("col-rs-diff",pp(row.excess21_pp))+
          td("col-rs-return",pct(valueAt(row,"return63")))+td("col-rs-return",pct(row.anchor_performance_3m))+td("col-rs-diff",pp(row.excess63_pp))+
          td("col-ema",ema(row,21))+td("col-ema",ema(row,50))+td("col-earnings",earnings(row.earnings_date))+'</tr>';
        return '<tr tabindex="-1" data-stock-symbol="'+esc(row.tradingview_symbol)+'">' +
          td("col-rank", row.display_rank || "N/A") +
          td("col-ticker", (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(row.ticker) + '</a>' : '<b>' + esc(row.ticker) + '</b>') + ' ' + customInfo([row.company,row.exchange,rationale].filter(Boolean).join(" · "), "Information for " + row.ticker)) +
          td("col-price", money(row.price_close)) +
          td("col-return", pct(row.daily_change)) +
          td("col-cap",marketCap(row.market_cap_usd)) +
          td("col-return", pct(valueAt(row,"return5"))) +
          td("col-return", pct(valueAt(row,"return21"))) +
          td("col-return", pct(valueAt(row,"return63"))) +
          td("col-ema", ema(row,21)) +
          td("col-ema", ema(row,50)) +
          td("col-return", finite(row.atr14_pct) ? row.atr14_pct.toFixed(2) + "%" : "N/A") +
          td("col-adv", money(row.adv30_usd,true)) +
          td("col-adv", money(row.turnover_1d_usd,true)) +
          td("col-relvol", finite(row.relative_volume_1d) ? row.relative_volume_1d.toFixed(2) : "N/A") +
          td("col-earnings", earnings(row.earnings_date)) + '</tr>';
      }).join("") || (hasCuratedList ? '<tr><td colspan="' + stockColumnCount + '">No stocks match these filters.</td></tr>' : "");
    }
    function download(name, text, type) {
      var url = URL.createObjectURL(new Blob([text], { type: type })),
        a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    $("theme-visible-csv").onclick = function () {
      download("themescope-visible-themes-" + data.session_date + ".csv", themeRowsToCsv(visibleThemes, data.session_date, data.dashboard_generated_at || data.generated_at), "text/csv;charset=utf-8");
      $("theme-export-status").textContent = visibleThemes.length + " visible sector/theme rows exported.";
    };
    $("csv").onclick = () => {
      download(
        "themescope-" + viewState.theme + "-" + data.session_date + ".csv",
        rowsToCsv(visible),
        "text/csv;charset=utf-8",
      );
      $("export-status").textContent =
        visible.length + " visible rows exported.";
    };

    render();
    showPage(viewState.page, { scroll: false });
    restoreRoute(firstView?.route_state);
    if (!history.state?.themescope) {
      try { history.replaceState({ themescope: true, index: 0, view: captureView() }, "", "#" + viewState.page); } catch (e) {}
    } else {
      replaceHistoryState();
    }
    updateBackControl();
    var scrollSaveTimer;
    window.addEventListener("scroll", function () {
      clearTimeout(scrollSaveTimer);
      scrollSaveTimer = setTimeout(function(){saveRoute();replaceHistoryState();}, 120);
    }, { passive: true, capture: true });
  }
  return {
    init: init,
    valueAt: valueAt,
    filterRows: filterRows,
    sortRows: sortRows,
    limitSelection: limitSelection,
    rowsToCsv: rowsToCsv,
    themeRowsToCsv: themeRowsToCsv,
    tradingViewExport: tradingViewExport,
    buildNavigationIndex:buildNavigationIndex, searchNavigation:searchNavigation, emaMatches:emaMatches,
    ranked: ranked,
    scoreBandClass: scoreBandClass,
    resolvedScoreBands: resolvedScoreBands,
    breadthThresholdClass: breadthThresholdClass,
    marketCap:marketCap, rsMatches:rsMatches,
    directionClass: directionClass, statusClass: statusClass, priorityCategory: priorityCategory, emaRelationship: emaRelationship, labels: LABELS,
  };
});
