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
  function priorityCategory(row) { return row.research_priority?.category || "observation"; }
  function themeRowsToCsv(rows, session, generatedAt) {
    var columns = ["rank_current", "rank_change_daily", "type", "theme_id", "name", "anchor_etf", "state", "research_priority", "theme_score", "current_strength", "medium_strength", "return5_pct", "return21_pct", "return63_pct", "theme_breadth21_pct", "theme_breadth21_above", "theme_breadth21_valid", "theme_breadth50_pct", "theme_breadth50_above", "theme_breadth50_valid", "configured_watchlist_count", "session_date", "generated_at"];
    var lines = [columns.map(csvEscape).join(",")];
    rows.forEach(function (row) {
      var b21 = row.theme_watchlist_breadth && row.theme_watchlist_breadth["21"] || {};
      var b50 = row.theme_watchlist_breadth && row.theme_watchlist_breadth["50"] || {};
      var values = [row.rank_current ?? row.global_rank, row.rank_change_daily,
        row.level === "Sector" ? "Sector" : "Theme", row.id, row.name, row.anchor, row.theme_state, row.research_priority?.label,
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
    $("score-method-description").textContent =
      "Theme Score = " + currentWeight + " Current + " + mediumWeight + " Medium.";
    var infoText = {
      priority: "Market direction and relative state determine a research group. Long labels require close above EMA50; short labels require close below EMA50. These are research priorities, not entry signals.",
      state: "Determined by whether Current and Medium are at least 50. Leading means both are in the stronger half; Improving means only Current is; Fading means only Medium is; Lagging means both are in the weaker half.",
      theme_score: currentWeight + " Current plus " + mediumWeight + " Medium. The color represents a relative score band, not a Long or Short signal.",
      current_strength_score: "The ETF's TradingView 1-month Performance, converted to an ascending average-rank percentile among the same eligible ETF set used for Medium.",
      medium_strength_score: "The ETF's TradingView 3-month Performance, converted to an ascending average-rank percentile among the same eligible ETF set used for Current.",
      theme_breadth21_pct: "The percentage of configured theme-watchlist stocks trading above EMA21. It does not affect Theme Score or state.",
      theme_breadth50_pct: "The percentage of configured theme-watchlist stocks trading above EMA50. It does not affect Theme Score or state.",
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
      var labels = {rank_current:"Current rank",state:"State",theme_score:"Theme Score",current_strength_score:"Current",medium_strength_score:"Medium",excess21:"1M versus SPY",excess63:"3M versus SPY",theme_breadth21_pct:"Above EMA21",theme_breadth50_pct:"Above EMA50"};
      var description = infoText[key] || LABELS[key]?.definition || "Methodology explanation unavailable.";
      var id = "themescope-info-" + key + "-" + (++infoCounter);
      return '<span class="info-control"><button class="info-button" type="button" id="' + id + '" data-tip-text="' + esc(description) + '" aria-label="Explain ' + esc(labels[key] || key) + '" aria-expanded="false">i</button></span>';
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
      const close = row.price_close;
      const average = row["ema" + period];
      return finite(close) && finite(average)
        ? close > average ? '<span class="positive">Above</span>' : close < average ? '<span class="negative">Below</span>' : '<span class="muted">At</span>'
        : missing;
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
    var state = {
      theme: initialTheme?.id, themeKey: "theme_score", themeDir: "desc",
      stockKey: "return21", stockDir: "desc", themeType: "All", themeState: "All", themePriority: "All",
      page: location.hash.slice(1) || "market", themeNavigationOrder: null
    };
    if (history.state?.themescope && history.state.view) {
      var firstView = history.state.view;
      state.theme = firstView.selected_theme_id || state.theme;
      state.themeSearch = firstView.theme_search || "";
      state.themeType = firstView.theme_type_filter || "All";
      state.themeState = firstView.theme_state_filter || "All";
      state.themePriority = firstView.theme_priority_filter || "All";
      state.themeKey = firstView.theme_sort_key || state.themeKey;
      state.themeDir = firstView.theme_sort_direction || state.themeDir;
      state.stockSearch = firstView.stock_search || "";
      state.stockEmaFilter = firstView.stock_ema_filter || "all";
      state.stockKey = firstView.stock_sort_key || state.stockKey;
      state.stockDir = firstView.stock_sort_direction || state.stockDir;
      state.themeSelectorSearch = firstView.theme_selector_search || "";
      state.themeNavigationOrder = firstView.theme_navigation_order || null;
      state.dailyMethodologyOpen = Boolean(firstView.daily_methodology_open);
      state.page = firstView.page || state.page;
    }
    function captureView() {
      if ($("theme-search")) state.themeSearch = $("theme-search").value;
      if ($("theme-type")) state.themeType = $("theme-type").value;
      if ($("theme-state")) state.themeState = $("theme-state").value;
      if ($("theme-sort")?.value) state.themeKey = $("theme-sort").value;
      if ($("stock-search")) state.stockSearch = $("stock-search").value;
      if ($("ema-filter")) state.stockEmaFilter = $("ema-filter").value;
      if ($("stock-sort")) state.stockKey = $("stock-sort").value;
      if ($("watchlist-theme-search")) state.themeSelectorSearch = $("watchlist-theme-search").value;
      if ($("daily-methodology")) state.dailyMethodologyOpen = $("daily-methodology").open;
      state.scroll_position = window.scrollY || 0;
      return {
        page: state.page, selected_theme_id: state.theme,
        theme_search: state.themeSearch || "", theme_type_filter: state.themeType,
        theme_state_filter: state.themeState, theme_priority_filter: state.themePriority, theme_sort_key: state.themeKey,
        theme_sort_direction: state.themeDir, stock_search: state.stockSearch || "",
        stock_ema_filter: state.stockEmaFilter || "all", stock_sort_key: state.stockKey,
        stock_sort_direction: state.stockDir,
        theme_selector_search: state.themeSelectorSearch || "",
        theme_navigation_order: state.themeNavigationOrder,
        daily_methodology_open: Boolean(state.dailyMethodologyOpen),
        scroll_position: state.scroll_position
      };
    }
    function replaceHistoryState() {
      var current = history.state;
      if (current && current.themescope) {
        try { history.replaceState({ themescope: true, index: current.index, view: captureView() }, "", "#" + state.page); } catch (e) {}
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
        var view = captureView();
        view.page = id;
        var previous = history.state;
        var index = previous && previous.themescope ? previous.index + 1 : 1;
        try { history.pushState({ themescope: true, index: index, view: view }, "", "#" + id); } catch (e) {}
      }
      state.page = id;
      closeInfoTooltip();
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
      if (navigation.scroll !== false) window.scrollTo(0, 0);
    }
    document.querySelectorAll(".side-nav [data-page]").forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        if (link.dataset.page !== state.page) showPage(link.dataset.page, { push: true });
      });
    });
    $("app-back").addEventListener("click", function () {
      if (!this.disabled && history.state?.themescope && history.state.index > 0) history.back();
    });
    window.addEventListener("popstate", function (event) {
      var view = event.state?.themescope ? event.state.view : null;
      if (!view) { updateBackControl(); return; }
      state.page = view.page || "market";
      state.theme = view.selected_theme_id || state.theme;
      state.themeSearch = view.theme_search || ""; state.themeType = view.theme_type_filter || "All";
      state.themePriority = view.theme_priority_filter || "All";
      state.themeState = view.theme_state_filter || "All"; state.themeKey = view.theme_sort_key || "theme_score";
      state.themeDir = view.theme_sort_direction || "desc"; state.stockSearch = view.stock_search || "";
      state.stockDir = view.stock_sort_direction || "desc";
      state.stockEmaFilter = view.stock_ema_filter || "all"; state.stockKey = view.stock_sort_key || "return21";
      state.themeSelectorSearch = view.theme_selector_search || ""; state.themeNavigationOrder = view.theme_navigation_order || null;
      state.dailyMethodologyOpen = Boolean(view.daily_methodology_open);
      state.scroll_position = view.scroll_position || 0;
      var fields = {"theme-search":"themeSearch","theme-type":"themeType","theme-state":"themeState","theme-priority":"themePriority","theme-sort":"themeKey","stock-search":"stockSearch","ema-filter":"stockEmaFilter","stock-sort":"stockKey","watchlist-theme-search":"themeSelectorSearch"};
      Object.keys(fields).forEach(function (id) { if ($(id) && state[fields[id]] !== undefined) $(id).value = state[fields[id]]; });
      render();
      $("daily-methodology").open = state.dailyMethodologyOpen;
      showPage(state.page, { scroll: false });
      window.scrollTo(0, state.scroll_position || 0);
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
    showPage(location.hash.slice(1) || "market", false);
    var decision = data.decision || data.market_classification?.decision || {};
    var classification = data.market_classification || {};
    function themeById(id) { return data.themes.find(function (row) { return row.id === id; }); }
    function priorityDefinition(key) {
      var definition = decision.priority_definitions?.[key] || {};
      var states = (definition.theme_states || []).join(" / ");
      return (states ? states + " · " : "") + (definition.labels || []).join(" / ") + (definition.ema50_guard ? " · " + definition.ema50_guard : "");
    }
    function dailyThemeLink(row) {
      if (!row) return "";
      var context = finite(row.price_close) && finite(row.ema50) ? (row.price_close > row.ema50 ? "Above EMA50" : row.price_close < row.ema50 ? "Below EMA50" : "At EMA50") : "EMA50 unavailable";
      return '<li><a class="priority-theme-link" href="#watchlist" data-daily-theme="' + esc(row.id) + '"><b>' + esc(row.name) + '</b><span>' + esc(row.anchor) + '</span><small>' + esc(row.theme_state || "Unavailable") + ' · ' + context + '</small><span>' + score(row, "theme_score") + '</span></a></li>';
    }
    function renderMethodology() {
      var marketRows = (decision.market_matrix || []).map(function(cell) {
        var active = decision.spy_price_state === cell.spy && decision.qqq_price_state === cell.qqq && decision.combined_breadth_state === cell.breadth;
        return '<tr' + (active ? ' class="active-cell"' : '') + '><td class="' + statusClass(cell.spy) + '">' + esc(cell.spy) + '</td><td class="' + statusClass(cell.qqq) + '">' + esc(cell.qqq) + '</td><td class="' + statusClass(cell.breadth) + '">' + esc(cell.breadth) + '</td><td class="' + directionClass(cell.direction) + '">' + esc(cell.direction) + '</td></tr>';
      });
      var priorityRows = ["Long bias","Selective long","Neutral","Selective short","Short bias","Unclassified"].map(function (direction) {
        var matrixRow = decision.priority_matrix?.[direction] || {};
        var labels = ["Leading","Improving","Fading","Lagging"].map(function (themeState) { return matrixRow[themeState] || "Unavailable"; });
        return '<tr' + (decision.market_classification === direction ? ' class="active-cell"' : '') + '><td class="' + directionClass(direction) + '">' + direction + '</td>' + labels.map(function (x) { return '<td>' + x + '</td>'; }).join("") + '</tr>';
      }).join("");
      $("methodology-content").innerHTML = '<h3>Market matrix</h3><table><thead><tr><th>SPY Price</th><th>QQQ Price</th><th>Combined Breadth</th><th>Result</th></tr></thead><tbody>' + marketRows.join("") + '</tbody></table><h3>Market × Theme State priorities</h3><table><thead><tr><th>Market</th><th>Leading</th><th>Improving</th><th>Fading</th><th>Lagging</th></tr></thead><tbody>' + priorityRows + '</tbody></table><p><b>EMA50 guard:</b> Long labels require the anchor close strictly above EMA50; short labels require it strictly below EMA50.</p><p><b>States:</b> Leading has Current and Medium at or above 50; Improving has only Current at or above 50; Fading has only Medium at or above 50; Lagging has both below 50.</p><p>Research Priority is not an entry signal.</p>';
    }
    function renderDailyPlan() {
      $("daily-session").textContent = sessionDisplay(decision.session_date || data.session_date);
      $("daily-generated").textContent = data.dashboard_generated_at_hkt_display || decision.generated_at_hkt || "Unavailable";
      $("daily-classification").className = "decision-tag " + directionClass(decision.market_classification);
      $("daily-classification").textContent = decision.market_classification || classification.direction || "Unclassified";
      $("daily-action").textContent = decision.action_sentence || classification.action_summary || "Required inputs unavailable.";
      var pathRows = [
        ["SPY Price State", decision.spy_price_state, "Primary vote", "market"],
        ["QQQ Price State", decision.qqq_price_state, "Primary vote", "market"],
        ["Combined Breadth", decision.combined_breadth_state, "Selective-tilt input or context"],
        ["IWM Price State", decision.iwm_price_state, "Context only, no vote"],
        ["Russell 2000 Breadth", decision.russell_2000_breadth_state, "Context only, no vote"],
        ["Final Market result", decision.market_classification, "Approved matrix output"],
      ];
      $("decision-path").innerHTML = '<div class="decision-row header" role="row"><span>Input</span><span>Current reading</span><span>Decision role</span></div>' + pathRows.map(function (row) { var reading = row[1] || "Unavailable"; return '<div class="decision-row" role="row"><span>' + (row[3] ? '<a href="#market" data-page-link="market">' + row[0] + '</a>' : row[0]) + '</span><span><span class="reading-tag ' + (row[0] === "Final Market result" ? directionClass(reading) : statusClass(reading)) + '">' + esc(reading) + '</span></span><span>' + row[2] + '</span></div>'; }).join("");
      $("why-result").innerHTML = '<p>' + esc(decision.reason || classification.reason || "Required inputs unavailable.") + '</p>';
      var labels = {primary:"Primary",secondary:"Secondary",exception:"Lower priority / exception",observation:"Observation only"};
      $("daily-priorities").innerHTML = ["primary","secondary","exception","observation"].map(function (key) {
        var ids = decision.priority_groups?.[key] || [], rows = ids.map(themeById).filter(Boolean);
        return '<article class="priority-card"><h3>' + labels[key] + '</h3><p class="priority-rule">' + esc(priorityDefinition(key) || (key === "observation" ? "No directional label or EMA50 guard not met." : "No active rule.")) + '</p><b class="priority-count">' + rows.length + '</b>' + (rows.length ? '<ul class="priority-theme-list">' + rows.slice(0,5).map(dailyThemeLink).join("") + '</ul>' : '<p class="muted">None today</p>') + '</article>';
      }).join("");
      var failures = decision.guard_failures || [];
      if (failures.length) {
        var byState = {};
        failures.forEach(function (failure) { var row=themeById(failure.theme_id); if (row) byState[row.theme_state]=(byState[row.theme_state]||0)+1; });
        $("qualification-summary").innerHTML = Object.keys(byState).map(function (themeState) { var total=data.themes.filter(function (row) { return row.theme_state === themeState; }).length; return '<p>' + total + ' ' + esc(themeState) + ' themes · ' + (total-byState[themeState]) + ' retain a directional priority · ' + byState[themeState] + ' remain Observation only because the anchor does not pass the EMA50 guard.</p>'; }).join("");
      } else $("qualification-summary").innerHTML = '<p>Theme State totals and priority totals reconcile without EMA50 guard failures.</p>';
      $("divergence-context").innerHTML = '<p>' + esc(decision.divergence || "Price direction and Breadth are aligned.") + '</p>';
      renderMethodology();
    }
    renderDailyPlan();
    $("daily-methodology").open = Boolean(state.dailyMethodologyOpen);
    $("daily-methodology").addEventListener("toggle", function () { state.dailyMethodologyOpen=this.open; replaceHistoryState(); });
    document.querySelectorAll("[data-page-link]").forEach(function (link) { link.addEventListener("click", function (event) { event.preventDefault(); showPage(link.dataset.pageLink, {push:true}); }); });
    $("daily-priorities").addEventListener("click", function (event) { var link=event.target.closest("[data-daily-theme]"); if (!link) return; event.preventDefault(); state.theme=link.dataset.dailyTheme; showPage("watchlist", {push:true}); render(); replaceHistoryState(); });
    if ($("market-direction")) {
      var primary = priorityDefinition("primary") || "None today", secondary = priorityDefinition("secondary") || "None today";
      $("market-direction").innerHTML='<div class="market-action-card"><div><h2 class="' + directionClass(decision.market_classification) + '">' + esc(decision.market_classification || classification.direction || "Unclassified") + '</h2></div><div class="market-action-details"><p>SPY ' + esc(decision.spy_price_state || "Unavailable") + ' + QQQ ' + esc(decision.qqq_price_state || "Unavailable") + ' → ' + esc(decision.market_classification || "Unclassified") + '</p><p>Combined Breadth: ' + esc(decision.combined_breadth_state || "Unavailable") + '</p><p>Primary: ' + esc(primary) + '</p><p>Secondary: ' + esc(secondary) + '</p></div><button type="button" class="open-plan">Open Daily Plan</button></div>';
      $("market-direction").querySelector(".open-plan").onclick=function(){showPage("daily-plan",{push:true});};
    }
    const marketWarnings = (data.context || []).filter((row) => [21, 50].some((period) => row.index_breadth?.[String(period)]?.status !== "valid")).map((row) => row.ticker + " breadth unavailable");
    $("status").textContent = (data.run_kind === "offline_historical_diagnostic" ? "Historical diagnostic · live completeness unverified · " : "") + marketWarnings.join(" · ");
    $("cards").innerHTML = data.context.map(function(row) {
      return '<article class="market-card"><header class="market-card-head"><div><div class="market-ticker">' + esc(row.ticker) + '</div><div class="market-title-sub">' + esc({SPY:"S&P 500 ETF",QQQ:"Nasdaq-100 ETF",IWM:"Russell 2000 ETF"}[row.ticker] || row.name) + '</div></div></header><div class="market-price-row"><span class="price">' + money(row.price_close) + '</span><span class="market-daily"><small>1D</small>' + pct(row.daily_change) + '</span></div><div class="market-returns">' + [["5","1W"],["21","1M"],["63","3M"]].map(function(w){return '<span><small>' + w[1] + '</small>' + pct(row.returns[w[0]]?.value) + '</span>';}).join("") + '</div>' + conditions(row) + '</article>';
    }).join("");
    document.querySelector(".volatility-section").hidden = !(data.volatility_context || []).length;
    $("volatility-card").innerHTML = (data.volatility_context || []).map(function (item) {
      const badge = item.source_status && item.source_status !== "available" ? '<span class="source-state source-missing">' + esc(item.source_status) + '</span>' : '';
      const percentile = finite(item.trailing_1y_percentile) ? 'Higher than ' + item.trailing_1y_percentile.toFixed(1) + '% of observations in the last ' + item.trailing_1y_observations + ' sessions.' : '1-year percentile unavailable.';
      const summary = item.vix_direction_summary || 'Volatility direction is mixed across the displayed periods.';
      return '<article class="market-card volatility-card"><div class="market-card-head"><div><div class="market-ticker">VIX</div><div class="market-title-sub">CBOE Volatility Index</div></div>' + badge + '</div>' +
        '<div class="vix-grid"><div><div class="price">' + (finite(item.level) ? item.level.toFixed(2) : "Unavailable") + '</div><div class="market-title-sub">1-year percentile ' + (finite(item.trailing_1y_percentile) ? item.trailing_1y_percentile.toFixed(1) : "Unavailable") + '</div></div>' +
        '<div class="vix-spark">' + spark(item.history, "close", "VIX closes") + '</div><div class="market-returns">' + vixChange("Today", item.daily_change, item.vix_direction_1d, item.source_reason) + vixChange("1 week", item.return5, item.vix_direction_5d, item.source_reason) + vixChange("1 month", item.return21, item.vix_direction_21d, item.source_reason) + '</div></div>' +
        '<p class="vix-context">' + esc(percentile) + '<br>' + esc(summary) + '</p><p class="market-observation">Data ' + esc(item.observation_date || "unavailable") + (item.retrieved_at_hkt_display ? ' · Retrieved ' + esc(item.retrieved_at_hkt_display) : "") + (item.source_reason ? ' · ' + esc(item.source_reason) : "") + '</p></article>';
    }).join("");
    var metrics = {
      rank_current: "Current rank",
      rank_change_daily: "Δ Rank",
      priority: "Research priority",
      theme_state: "State",
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
      return '<label>Search <input id="stock-search" placeholder="Ticker or company"></label>' +
        '<label>Sort by <select id="stock-sort">' + options([["return5","1W Performance"],["return21","1M Performance"],["return63","3M Performance"],["adv30_usd","Avg $Vol30"],["turnover_1d_usd","Turnover 1D"],["relative_volume_1d","Relative Volume"],["price_close","Price"]]) +
        '</select></label><button id="stock-direction" type="button"></button>' +
        '<label>EMA <select id="ema-filter"><option value="all">All</option><option value="above21">Above EMA21</option><option value="below21">At/below EMA21</option><option value="above50">Above EMA50</option><option value="below50">At/below EMA50</option></select></label>';
    }
    $("theme-controls").innerHTML = '<label>Search <input id="theme-search" placeholder="Sector, theme or ETF"></label>' +
      '<label>Type <select id="theme-type"><option>All</option><option>Sector</option><option>Theme</option></select></label>' +
      '<label>State <select id="theme-state"><option>All</option><option>Leading</option><option>Improving</option><option>Fading</option><option>Lagging</option></select></label>' +
      '<label>Research Priority <select id="theme-priority"><option value="All">All</option><option value="primary">Primary</option><option value="secondary">Secondary</option><option value="exception">Exceptions</option><option value="observation">Observation only</option></select></label>' +
      '<label>Sort by <select id="theme-sort">' + options(Object.entries(metrics).filter(([key]) => !["price_close","adv30_usd","name"].includes(key))) + '</select></label>' +
      '<button id="theme-direction" type="button"></button>';
    $("stock-controls").innerHTML = stockControls();
    $("theme-search").value = state.themeSearch || "";
    $("theme-type").value = state.themeType;
    $("theme-state").value = state.themeState;
    $("theme-priority").value = state.themePriority;
    $("theme-priority").onchange = function(){state.themePriority=this.value;render();persistView();};
    $("theme-sort").value = state.themeKey;
    $("stock-search").value = state.stockSearch || "";
    $("stock-sort").value = state.stockKey;
    $("ema-filter").value = state.stockEmaFilter || "all";
    $("watchlist-theme-search").value = state.themeSelectorSearch || "";
    function persistView() { replaceHistoryState(); }
    $("theme-sort").onchange = function () { state.themeKey = this.value; render(); persistView(); };
    $("theme-direction").onclick = function () { state.themeDir = state.themeDir === "desc" ? "asc" : "desc"; render(); persistView(); };
    $("theme-search").addEventListener("input", function () { state.themeSearch = this.value; render(); persistView(); });
    $("theme-type").onchange = function () { state.themeType = this.value; render(); persistView(); };
    $("theme-state").onchange = function () { state.themeState = this.value; render(); persistView(); };
    $("stock-sort").onchange = function () { state.stockKey = this.value; render(); persistView(); };
    $("stock-direction").onclick = function () { state.stockDir = state.stockDir === "desc" ? "asc" : "desc"; render(); persistView(); };
    $("stock-search").addEventListener("input", function () { state.stockSearch = this.value; render(); persistView(); });
    $("ema-filter").onchange = function () { state.stockEmaFilter = this.value; render(); persistView(); };
    $("watchlist-theme-search").addEventListener("input", function () { state.themeSelectorSearch = this.value; renderThemeSelector(); persistView(); });
    function filtered(rows, p) {
      if (p === "theme") {
        const query = $("theme-search").value.trim().toLowerCase();
        return rows.filter(function (row) {
          const matchesText = !query || [row.name, row.anchor, row.id].some((v) => String(v || "").toLowerCase().includes(query));
          const type = row.level === "Sector" ? "Sector" : "Theme";
          const matchesType = state.themeType === "All" || type === state.themeType;
          const matchesState = state.themeState === "All" || row.theme_state === state.themeState;
          return matchesText && matchesType && matchesState && (state.themePriority === "All" || priorityCategory(row) === state.themePriority);
        });
      }
      return filterRows(rows, { query: $("stock-search").value }).filter(function (row) {
        const filter = $("ema-filter").value;
        if (filter === "all") return true;
        const period = filter.endsWith("21") ? 21 : 50;
        if (!finite(row.price_close) || !finite(row["ema" + period])) return false;
        return filter.startsWith("above") ? row.price_close > row["ema" + period] : row.price_close <= row["ema" + period];
      });
    }
    function renderThemeSelector() {
      var query = ($("watchlist-theme-search").value || "").trim().toLowerCase();
      var match = function (row) { return !query || [row.name, row.anchor, row.id].some(function (v) { return String(v || "").toLowerCase().includes(query); }) || row.id === state.theme; };
      var sectorOptions = (data.themes || []).filter((row) => row.level === "Sector" && match(row)).map((row) => '<option value="' + esc(row.id) + '">' + esc(row.name) + ' · ' + esc(row.anchor) + '</option>').join("");
      var themeOptions = (data.themes || []).filter((row) => row.level !== "Sector" && match(row)).map((row) => '<option value="' + esc(row.id) + '">' + esc(row.name) + ' · ' + esc(row.anchor) + '</option>').join("");
      $("watchlist-theme-selector").innerHTML = '<optgroup label="Sectors">' + (sectorOptions || '<option disabled>No matching sectors</option>') + '</optgroup><optgroup label="Themes">' + (themeOptions || '<option disabled>No matching themes</option>') + '</optgroup>';
      if ((data.themes || []).some((row) => row.id === state.theme)) $("watchlist-theme-selector").value = state.theme;
    }
    function themeNavigationOrder() {
      var allIds = new Set((data.themes || []).map((row) => row.id));
      var order = (state.themeNavigationOrder || []).filter((id) => allIds.has(id));
      return order.length > 0 ? order : sortRows(data.themes || [], "theme_score", "desc").map((row) => row.id);
    }
    function switchTheme(id, order) {
      if (!id || id === state.theme) return;
      state.themeNavigationOrder = order || state.themeNavigationOrder;
      state.theme = id;
      showPage("watchlist", { push: true });
      render();
      replaceHistoryState();
    }
    $("watchlist-theme-selector").onchange = function () { switchTheme(this.value); };
    $("previous-theme").onclick = function () {
      var order = themeNavigationOrder(), index = order.indexOf(state.theme);
      if (index < 0) index = 0;
      if (order.length) switchTheme(order[(index - 1 + order.length) % order.length], order);
    };
    $("next-theme").onclick = function () {
      var order = themeNavigationOrder(), index = order.indexOf(state.theme);
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
                ? '<button data-sort="' + c[1] + '" title="Sort by ' + esc(fullLabel) + '; unavailable values stay last" aria-label="Sort by ' + esc(fullLabel) + '">' + c[0] + (state[p + "Key"] === c[1] ? arrowIcon(state[p + "Dir"]) : "") + '</button>'
                : '<span title="' + esc(fullLabel) + '">' + c[0] + '</span>';
              var sortState = c[1] ? (state[p + "Key"] === c[1] ? (state[p + "Dir"] === "asc" ? "ascending" : "descending") : "none") : null;
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
              state[p + "Dir"] =
                state[p + "Key"] === key && state[p + "Dir"] === "desc"
                  ? "asc"
                  : "desc";
              state[p + "Key"] = key;
              if ($(p + "-sort")) $(p + "-sort").value = key;
              render();
              persistView();
            }),
        );
    }
    function td(columnClass, content, extraAttributes) {
      return '<td class="' + columnClass + '"' + (extraAttributes || '') + '>' + content + '</td>';
    }
    function themeStateType(value) {
      if (value === "Leading") return "leading";
      if (value === "Improving") return "improving";
      if (value === "Fading") return "fading";
      if (value === "Lagging") return "lagging";
      return "unavailable";
    }
    function stateBadge(value) {
      const help = value === "Improving"
        ? "Current score is in the stronger half while medium score is in the weaker half. This does not prove a reversal or rotation."
        : value === "Fading"
          ? "Current score is in the weaker half while medium score is in the stronger half. This does not prove a reversal or rotation."
        : "Cross-sectional state from Current and Medium relative-strength percentiles.";
      return '<span class="state-tag state-' + themeStateType(value) + '" aria-label="' + esc(value || "State unavailable") + ': ' + esc(help) + '">' + esc(value || "N/A") + "</span>";
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
      state.themeNavigationOrder = visibleThemes.map((row) => row.id);
      state.theme = id;
      showPage("watchlist", { push: true });
      render();
      replaceHistoryState();
    }
    $("theme-body").addEventListener("click", function (event) {
      var row = event.target.closest("tr[data-theme]");
      if (row && !event.target.closest("a")) select(row.dataset.theme);
    });
    var visible = [];
    var visibleThemes = [];
    function render() {
      closeInfoTooltip();
      setDirectionButton($("stock-direction"), state.stockDir);
      setDirectionButton($("theme-direction"), state.themeDir);
      var all = sortRows(data.themes || [], state.themeKey, state.themeDir).map((row) => Object.assign({}, row, { display_rank: row.global_rank }));
      visibleThemes = filtered(all, "theme");
      renderThemeSelector();
      const breadthUnavailable = visibleThemes.filter((row) => row.breadth_status_21 !== "valid" || row.breadth_status_50 !== "valid").length;
      $("theme-count").textContent = visibleThemes.length + " of " + all.length + " exposures" + (breadthUnavailable ? " · " + breadthUnavailable + " with breadth unavailable" : "");
      const themeColumns = [
        ["#", "rank_current", null, "rank_current", "Current rank", "col-rank"], ["Δ Rank", "rank_change_daily", null, "rank_change_daily", "Previous-session rank minus current-session rank", "col-rank-daily"], ["Name", "name", null, null, "Sector or theme name with exposure type", "col-name"], ["ETF", null, null, null, "Anchor ETF", "col-etf"], ["State", "theme_state", null, "state", "State", "col-state"],
        ["Research priority", "priority", null, "priority", "Directional research priority with an absolute EMA50 guard; not an entry signal.", "col-priority"], ["Score", "theme_score", null, "theme_score", "Theme Score", "col-score"], ["Current", "current_strength_score", null, "current_strength_score", "1-month Performance percentile", "col-score"], ["Medium", "medium_strength_score", null, "medium_strength_score", "3-month Performance percentile", "col-score"],
        ["1W", "return5", null, null, "TradingView 1-week Performance; context only", "col-return"], ["1M", "return21", null, null, "TradingView 1-month Performance", "col-return"], ["3M", "return63", null, null, "TradingView 3-month Performance", "col-return"], ["EMA50", null, null, null, "Anchor price relative to EMA50", "col-ema"],
        ["% > EMA21", "theme_breadth21_pct", null, "theme_breadth21_pct", "Available when at least eight configured members and 80 percent coverage have valid Price, EMA21 and EMA50 values. Does not affect Theme Score or state.", "col-breadth"], ["% > EMA50", "theme_breadth50_pct", null, "theme_breadth50_pct", "Available when at least eight configured members and 80 percent coverage have valid Price, EMA21 and EMA50 values. Does not affect Theme Score or state.", "col-breadth"],
      ];
      $("theme-cols").innerHTML = themeColumns.map(function (column) { return '<col class="' + column[5] + '">'; }).join("");
      head("theme", themeColumns);
      $("theme-body").innerHTML = visibleThemes.map(function (row) {
        const type = row.level === "Sector" ? "Sector" : "Theme";
        return '<tr data-theme="' + esc(row.id) + '" class="' + (row.id === state.theme ? "active " : "") + (priorityCategory(row) === "primary" ? "primary-row primary-" + row.research_priority.side : "") + '">' +
          td("col-rank", row.display_rank ?? "N/A") +
          td("col-rank-daily", finite(row.rank_change_daily) ? '<span class="' + (row.rank_change_daily > 0 ? "positive" : row.rank_change_daily < 0 ? "negative" : "muted") + '">' + (row.rank_change_daily > 0 ? "+" : "") + row.rank_change_daily + '</span>' : "N/A") +
          td("col-name", '<div class="theme-name-cell"><span class="type-tag">' + type + '</span><button class="theme-select" aria-label="Open watchlist for ' + esc(row.name) + '">' + esc(row.name) + '</button></div>') +
          td("col-etf", row.chart_url ? '<a href="' + esc(row.chart_url) + '" target="_blank" rel="noopener noreferrer">' + esc(row.anchor) + '</a>' : esc(row.anchor)) +
          td("col-state", stateBadge(row.theme_state)) +
          td("col-priority", '<span title="'+esc(row.research_priority?.reason || "Required inputs unavailable")+'">'+esc(row.research_priority?.label || "No directional priority")+'</span>') +
          td("col-score", score(row, "theme_score")) +
          td("col-score", score(row, "current_strength_score")) +
          td("col-score", score(row, "medium_strength_score")) +
          td("col-return", pct(valueAt(row, "return5"))) +
          td("col-return", pct(valueAt(row, "return21"))) +
          td("col-return", pct(valueAt(row, "return63"))) +
          td("col-ema", ema(row, 50)) +
          td("col-breadth", themeBreadthCell(row, 21)) +
          td("col-breadth", themeBreadthCell(row, 50)) + '</tr>';
      }).join("") || '<tr><td colspan="15">No eligible ETF exposures are available in this snapshot.</td></tr>';
      var selected = data.themes.find((row) => row.id === state.theme) || data.themes[0];
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
        $("tv").disabled = true;
        return;
      }
      $("csv").disabled = false;
      $("tv").disabled = false;
      $("stock-exports").hidden = false;
      $("stock-controls").hidden = false;
      $("stock-table-wrap").hidden = false;
      $("watchlist-message").hidden = true;
      $("active-name").textContent = selected.name
        ? selected.name + (selected.anchor ? " / " + selected.anchor : "")
        : "Watchlist";
      $("active-summary").innerHTML = '<div class="summary-scores">' + stateBadge(selected.theme_state) + ' ' + score(selected, "theme_score") + ' ' + score(selected, "current_strength_score") + ' ' + score(selected, "medium_strength_score") + '</div>' +
        '<div class="summary-returns"><span>1W Performance ' + pct(valueAt(selected, "return5")) + '</span><span>1M Performance ' + pct(valueAt(selected, "return21")) + '</span><span>3M Performance ' + pct(valueAt(selected, "return63")) + '</span></div>' +
        '<div class="summary-rank">Rank ' + (selected.rank_current ?? selected.global_rank ?? "unavailable") + ' of ' + data.themes.length + '</div>' +
        '<div class="summary-breadth">Theme breadth — EMA21 ' + breadthSummary(selected, 21) + ' · EMA50 ' + breadthSummary(selected, 50) + '</div>' +
        '<div class="summary-returns"><span>Anchor EMA21 ' + ema(selected, 21) + '</span><span>Anchor EMA50 ' + ema(selected, 50) + '</span></div>';
      var base = (selected.selected || []).slice();
      base = base.map((row) => Object.assign({}, row, { theme_id: selected.id, theme_name: selected.name, generated_at: data.dashboard_generated_at || data.generated_at }));
      visible = filtered(sortRows(base, state.stockKey, state.stockDir).map((row) => Object.assign({}, row, { display_rank: row.selection_slot })), "stock");
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
        $("tv").disabled = true;
      } else {
        const capacity = Number(data.settings?.watchlist_capacity || 20);
        $("coverage").textContent = base.length + " of " + capacity + " stocks";
      }
      var stockColumns = [
        ["#",null,null,null,"Configured position","col-rank"], ["Ticker",null,null,null,"Stock ticker; information includes company, exchange and membership rationale","col-ticker"],
        ["Price","price_close",null,null,"Stock Price","col-price"], ["1D","daily_change",null,null,"TradingView one-day price change percent","col-return"],
        ["1W","return5",null,null,"TradingView 1W Performance percent","col-return"], ["1M","return21",null,null,"TradingView 1M Performance percent","col-return"], ["3M","return63",null,null,"TradingView 3M Performance percent","col-return"],
        ["EMA21",null,null,null,"Stock Price vs EMA21","col-ema"], ["EMA50",null,null,null,"Stock Price vs EMA50","col-ema"],
        ["ATR%14","atr14_pct",null,"atr14_pct",LABELS.atr14_pct.definition,"col-return"], ["Avg $Vol30","adv30_usd",null,"adv30_usd",LABELS.adv30_usd.definition,"col-adv"],
        ["Turnover 1D","turnover_1d_usd",null,"turnover_1d_usd",LABELS.turnover_1d_usd.definition,"col-adv"], ["Rel Vol","relative_volume_1d",null,"relative_volume_1d",LABELS.relative_volume_1d.definition,"col-relvol"], ["Earnings",null,null,null,"Upcoming earnings; full date in accessible label","col-earnings"]
      ];
      $("stock-cols").innerHTML = stockColumns.map(function(c){return '<col class="' + c[5] + '">';}).join("");
      head("stock", stockColumns);
      $("stock-body").innerHTML = visible.map(function (row) {
        const url = row.chart_url || null;
        const rationale = row.membership_rationale || row.evidence_note || "Business relevance rationale recorded in the membership source.";
        return '<tr>' +
          td("col-rank", row.display_rank || "N/A") +
          td("col-ticker", (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(row.ticker) + '</a>' : '<b>' + esc(row.ticker) + '</b>') + ' ' + customInfo([row.company,row.exchange,rationale].filter(Boolean).join(" · "), "Information for " + row.ticker)) +
          td("col-price", money(row.price_close)) +
          td("col-return", pct(row.daily_change)) +
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
      }).join("") || (hasCuratedList ? '<tr><td colspan="14">No stocks match these filters.</td></tr>' : "");
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
        "themescope-" + state.theme + "-" + data.session_date + ".csv",
        rowsToCsv(visible),
        "text/csv;charset=utf-8",
      );
      $("export-status").textContent =
        visible.length + " visible rows exported.";
    };
    $("tv").onclick = () => {
      var selected = data.themes.find(function (row) { return row.id === state.theme; });
      var result = tradingViewExport([selected].concat(selected.selected || []));
      result.text = "###" + selected.name.replace(/,/g, " ") + " (" + selected.anchor + ")," + result.text;
      download("themescope-" + state.theme + ".txt", result.text, "text/plain");
      $("export-status").textContent =
        result.count +
        " symbols exported; " +
        result.omitted +
        " without verified exchange omitted.";
    };
    render();
    showPage(state.page, { scroll: false });
    if (!history.state?.themescope) {
      try { history.replaceState({ themescope: true, index: 0, view: captureView() }, "", "#" + state.page); } catch (e) {}
    } else {
      replaceHistoryState();
    }
    updateBackControl();
    var scrollSaveTimer;
    window.addEventListener("scroll", function () {
      clearTimeout(scrollSaveTimer);
      scrollSaveTimer = setTimeout(replaceHistoryState, 120);
    }, { passive: true });
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
    ranked: ranked,
    scoreBandClass: scoreBandClass,
    resolvedScoreBands: resolvedScoreBands,
    breadthThresholdClass: breadthThresholdClass,
    directionClass: directionClass, statusClass: statusClass, priorityCategory: priorityCategory, labels: LABELS,
  };
});
