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

  function scoreBandClass(value, bands) {
    if (!finiteNumber(value)) return "score-na";
    var band = (bands || []).find(function (item) {
      return value >= item.min && (value < item.max || item.max === 100 && value <= 100);
    });
    return band ? band.class : "score-na";
  }

  function themeRowsToCsv(rows, session, generatedAt) {
    var columns = ["rank_current", "rank_t_minus_5", "rank_change_5", "historical_rank_peer_count", "historical_rank_status", "historical_rank_reason", "type", "name", "anchor_etf", "state", "theme_score", "current_strength", "medium_strength", "return21_pct", "excess21_pp", "return63_pct", "excess63_pp", "holdings_breadth21_pct", "breadth21_above", "breadth21_valid", "breadth21_t_minus_5", "breadth21_change_5_pp", "holdings_breadth50_pct", "breadth50_above", "breadth50_valid", "breadth50_t_minus_5", "breadth50_change_5_pp", "holdings_asof", "score_status", "score_reason", "session_date", "generated_at"];
    var lines = [columns.map(csvEscape).join(",")];
    rows.forEach(function (row) {
      var b21 = row.holdings_breadth && row.holdings_breadth["21"] || {};
      var b50 = row.holdings_breadth && row.holdings_breadth["50"] || {};
      var values = [row.rank_current ?? row.global_rank, row.rank_t_minus_5, row.rank_change_5,
        row.historical_rank_peer_count, row.historical_rank_status, row.historical_rank_reason,
        row.level === "Sector" ? "Sector" : "Theme", row.name, row.anchor, row.theme_state,
        row.theme_score, row.current_strength_score, row.medium_strength_score,
        finiteNumber(valueAt(row, "return21")) ? valueAt(row, "return21") * 100 : null, finiteNumber(valueAt(row, "excess21")) ? valueAt(row, "excess21") * 100 : null,
        finiteNumber(valueAt(row, "return63")) ? valueAt(row, "return63") * 100 : null, finiteNumber(valueAt(row, "excess63")) ? valueAt(row, "excess63") * 100 : null,
        row.etf_breadth21_pct, b21.above_count, b21.valid_count, row.breadth21_t_minus_5, row.breadth21_change_5_pp,
        row.etf_breadth50_pct, b50.above_count, b50.valid_count, row.breadth50_t_minus_5, row.breadth50_change_5_pp,
        row.holdings_asof, row.field_status?.theme_score?.status, row.field_status?.theme_score?.reason, session, generatedAt];
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
      "return5",
      "selection_slot",
      "selection_queue",
      "ticker",
      "company",
      "exchange",
      "membership_tag",
      "membership_source",
      "membership_rationale",
      "is_anchor_holding",
      "above_ema21",
      "above_ema50",
      "evidence_category",
      "evidence_note",
      "etf_weight_pct",
      "adv30_usd",
      "return21",
      "return63",
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
        return5: valueAt(row, "return5"),
        theme_id: row.theme_id,
        selection_slot: row.selection_slot,
        selection_queue: row.selection_queue,
        ticker: row.ticker,
        company: row.company,
        exchange: row.exchange,
        membership_tag: row.membership_tag,
        membership_source: row.membership_source,
        membership_rationale: row.membership_rationale,
        is_anchor_holding: row.is_anchor_holding,
        above_ema21:
          row.price_close != null && row.ema21 != null
            ? row.price_close > row.ema21
            : null,
        above_ema50:
          row.price_close != null && row.ema50 != null
            ? row.price_close > row.ema50
            : null,
        evidence_category: row.evidence_category,
        evidence_note: row.evidence_note,
        etf_weight_pct: row.etf_weight_pct,
        adv30_usd: row.adv30_usd,
        return21: valueAt(row, "return21"),
        return63: valueAt(row, "return63"),
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
      var exchange = String(row.exchange || "").toUpperCase();
      var prefix =
        exchange.indexOf("NASDAQ") === 0
          ? "NASDAQ"
          : exchange.indexOf("NYSE") === 0
            ? "NYSE"
            : "";
      if (!prefix) {
        omitted += 1;
        return;
      }
      var key = prefix + ":" + row.ticker;
      if (seen.has(key)) {
        duplicates += 1;
        return;
      }
      seen.add(key);
      symbols.push(key);
    });
    return {
      text: symbols.join("\n") + (symbols.length ? "\n" : ""),
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
      '<span title="Input unavailable; see diagnostic export">—</span>';
    var scoreConfig = data.score_methodology || {};
    var scoreBands = data.ui_configuration?.score_bands || [];
    var currentWeights = scoreConfig.current_strength_weights || {};
    var mediumWeights = scoreConfig.medium_strength_weights || {};
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
      state: "Determined by whether Current and Medium are at least 50. Leading means both are in the stronger half; Improving means only Current is; Fading means only Medium is; Lagging means both are in the weaker half.",
      theme_score: currentWeight + " Current plus " + mediumWeight + " Medium. It provides a consistent relative-performance ranking for manual review and is not a prediction or entry signal.",
      current_strength_score: "The ETF's 21-session return minus SPY's 21-session return, converted to a percentile among all eligible sector/theme ETFs. A value of 50 is the middle of the current ranking universe.",
      medium_strength_score: "The ETF's 63-session return minus SPY's 63-session return, converted to a percentile among all eligible sector/theme ETFs.",
      excess21: "The ETF's 21-session percentage return minus SPY's 21-session percentage return, expressed in percentage points.",
      excess63: "The ETF's 63-session percentage return minus SPY's 63-session percentage return, expressed in percentage points.",
      etf_breadth21_pct: "The percentage of valid equity holdings in the anchor ETF trading above EMA21. This describes participation and does not determine the ETF's score or state.",
      etf_breadth50_pct: "The percentage of valid equity holdings in the anchor ETF trading above EMA50. This describes participation and does not determine the ETF's score or state."
    };
    var infoCounter = 0;
    function infoControl(key) {
      var labels = {state:"State",theme_score:"Theme Score",current_strength_score:"Current",medium_strength_score:"Medium",excess21:"1M versus SPY",excess63:"3M versus SPY",etf_breadth21_pct:"Above EMA21",etf_breadth50_pct:"Above EMA50"};
      var id = "themescope-tip-" + key + "-" + (++infoCounter);
      return '<span class="info-control"><button class="info-button" type="button" aria-label="Explain ' + esc(labels[key] || key) + '" aria-describedby="' + id + '" aria-expanded="false">i</button><span class="info-tip" role="tooltip" id="' + id + '">' + esc(infoText[key] || "Methodology explanation unavailable.") + '</span></span>';
    }
    document.addEventListener("click", function (event) {
      var button = event.target.closest(".info-button");
      document.querySelectorAll(".info-control.open").forEach(function (control) {
        if (!button || !control.contains(button)) {
          control.classList.remove("open");
          control.querySelector(".info-button")?.setAttribute("aria-expanded", "false");
        }
      });
      if (button) {
        var control = button.closest(".info-control");
        var open = control.classList.toggle("open");
        button.setAttribute("aria-expanded", String(open));
      }
    });
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
            '">—</span>';
    }
    function score(row, key) {
      const value = row[key];
      const bandClass = scoreBandClass(value, scoreBands);
      const label = finite(value) ? value.toFixed(1) : "—";
      return '<span class="score-chip ' + esc(bandClass) + '" aria-label="' + esc(finite(value) ? label + " score" : "Score unavailable") + '">' + label + '</span>';
    }
    function breadth(row, period, index = false) {
      const m = (index ? row.index_breadth : row.holdings_breadth)?.[
        String(period)
      ];
      if (!m || m.value === null || m.status !== "valid")
        return (
          '<span title="' +
          esc(m?.reason || "Breadth is unavailable or fails its configured sample, freshness, or completeness rule") +
          '">—</span>'
        );
      return (
        '<span class="' +
        (m.status === "valid" ? "" : "warning") +
        '" title="' +
        esc(
        (m.reason || "Valid") +
            "; above EMA: " + m.above_count + "/" + m.valid_count +
            "; holdings as of " +
            m.as_of,
        ) +
        '">' +
        m.value.toFixed(1) +
        "% <small>(" +
            m.above_count +
            "/" +
            m.valid_count +
            ")</small>" +
        (m.status === "valid" ? "" : " ⚠") +
        "</span>"
      );
    }
    function marketBreadth(row, period) {
      const m = row.index_breadth?.[String(period)];
      const title = (row.ticker === "IWM" ? "Holdings" : "Constituents") + " above EMA" + period;
      const change = row["breadth" + period + "_change_5_pp"];
      const changeLine = finite(change)
        ? '<small class="breadth-change ' + (change > 0 ? "positive" : change < 0 ? "negative" : "") + '">5-session change ' + (change > 0 ? "+" : "") + change.toFixed(1) + ' pp</small>'
        : '<small class="breadth-change" title="' + esc(row.field_status?.["breadth" + period + "_change_5_pp"]?.reason || "Both observations must pass the breadth validity rule") + '">5-session change unavailable</small>';
      if (!m || !finite(m.value) || m.status !== "valid") {
        const count = m && finite(m.valid_count) && finite(m.eligible_count) ? m.valid_count.toLocaleString("en-US") + "/" + m.eligible_count.toLocaleString("en-US") + " mapped" : "Counts unavailable";
        const reason = m?.reason || "Price history unavailable";
        const shortReason = /coverage/i.test(reason) ? "Insufficient price history" : reason.replace(/\b\d+(?:\.\d+)?%/g, "").replace(/\s{2,}/g, " ").trim();
        const changeReason = row.field_status?.["breadth" + period + "_change_5_pp"]?.reason || "Both observations must pass the breadth validity rule";
        const diagnostic = "Breadth unavailable · " + count + " · " + reason + " · 5-session change unavailable: " + changeReason;
        return '<div class="indicator-box"><div class="indicator-label">' + title + '</div><div class="breadth-unavailable" title="' + esc(diagnostic) + '"><b>Breadth unavailable</b><small>' + esc(count) + '</small><small class="breadth-reason">' + esc(shortReason) + '</small><small class="breadth-change">5-session change unavailable</small></div></div>';
      }
      return '<div class="indicator-box"><div class="indicator-label">' + title + '</div><div class="breadth-row"><b class="breadth-value">' + m.value.toFixed(1) + '%</b><span class="breadth-count">' + m.above_count.toLocaleString("en-US") + '/' + m.valid_count.toLocaleString("en-US") + '</span></div><div class="meter"><i style="width:' + Math.max(0, Math.min(100, m.value)) + '%"></i></div>' + changeLine + '</div>';
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
      const breadthTitle = row.ticker === "IWM" ? "IWM holdings breadth" : "Market breadth";
      const trendTitle = row.ticker === "IWM" ? "ETF trend" : "Index trend";
      return '<section class="market-section"><h3 class="market-section-title">' + breadthTitle + '</h3><div class="market-indicators">' + marketBreadth(row, 21) + marketBreadth(row, 50) + '</div></section>' +
        '<section class="market-section"><h3 class="market-section-title">' + trendTitle + '</h3><div class="condition-row">' + conditionCard(row, 21) + conditionCard(row, 50) + '</div></section>' +
        '<p class="market-observation">' + (row.ticker === "IWM" ? "iShares holdings proxy · as of " : "Constituent list · as of ") + esc(row.index_constituent_asof || "date unavailable") + '</p>';
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
            '">—</span>'
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
    var pageIds = ["market", "sectors-themes", "watchlist"];
    var initialTheme = data.themes.find((t) => (t.selected || []).length) || data.themes[0];
    var state = {
      theme: initialTheme?.id, themeKey: "theme_score", themeDir: "desc",
      stockKey: "excess21", stockDir: "desc", themeType: "All", themeState: "All",
      page: location.hash.slice(1) || "market", themeNavigationOrder: null
    };
    if (history.state?.themescope && history.state.view) {
      var firstView = history.state.view;
      state.theme = firstView.selected_theme_id || state.theme;
      state.themeSearch = firstView.theme_search || "";
      state.themeType = firstView.theme_type_filter || "All";
      state.themeState = firstView.theme_state_filter || "All";
      state.themeKey = firstView.theme_sort_key || state.themeKey;
      state.themeDir = firstView.theme_sort_direction || state.themeDir;
      state.stockSearch = firstView.stock_search || "";
      state.stockEmaFilter = firstView.stock_ema_filter || "all";
      state.stockKey = firstView.stock_sort_key || state.stockKey;
      state.stockDir = firstView.stock_sort_direction || state.stockDir;
      state.stockRowLimit = firstView.stock_row_limit || String(data.settings?.watchlist_default_limit || 15);
      state.themeSelectorSearch = firstView.theme_selector_search || "";
      state.themeNavigationOrder = firstView.theme_navigation_order || null;
      state.page = firstView.page || state.page;
    }
    function captureView() {
      if ($("theme-search")) state.themeSearch = $("theme-search").value;
      if ($("theme-type")) state.themeType = $("theme-type").value;
      if ($("theme-state")) state.themeState = $("theme-state").value;
      if ($("theme-sort")) state.themeKey = $("theme-sort").value;
      if ($("stock-search")) state.stockSearch = $("stock-search").value;
      if ($("ema-filter")) state.stockEmaFilter = $("ema-filter").value;
      if ($("stock-sort")) state.stockKey = $("stock-sort").value;
      if ($("pool")) state.stockRowLimit = $("pool").value;
      if ($("watchlist-theme-search")) state.themeSelectorSearch = $("watchlist-theme-search").value;
      state.scroll_position = window.scrollY || 0;
      return {
        page: state.page, selected_theme_id: state.theme,
        theme_search: state.themeSearch || "", theme_type_filter: state.themeType,
        theme_state_filter: state.themeState, theme_sort_key: state.themeKey,
        theme_sort_direction: state.themeDir, stock_search: state.stockSearch || "",
        stock_ema_filter: state.stockEmaFilter || "all", stock_sort_key: state.stockKey,
        stock_sort_direction: state.stockDir, stock_row_limit: state.stockRowLimit || "15",
        theme_selector_search: state.themeSelectorSearch || "",
        theme_navigation_order: state.themeNavigationOrder,
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
      document.querySelectorAll(".page").forEach(function (page) {
        page.hidden = page.id !== id;
      });
      document.querySelectorAll(".side-nav [data-page]").forEach(function (link) {
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
      state.themeState = view.theme_state_filter || "All"; state.themeKey = view.theme_sort_key || "theme_score";
      state.themeDir = view.theme_sort_direction || "desc"; state.stockSearch = view.stock_search || "";
      state.stockEmaFilter = view.stock_ema_filter || "all"; state.stockKey = view.stock_sort_key || "excess21";
      state.stockDir = view.stock_sort_direction || "desc"; state.stockRowLimit = view.stock_row_limit || "15";
      state.themeSelectorSearch = view.theme_selector_search || ""; state.themeNavigationOrder = view.theme_navigation_order || null;
      state.scroll_position = view.scroll_position || 0;
      var fields = {"theme-search":"themeSearch","theme-type":"themeType","theme-state":"themeState","theme-sort":"themeKey","stock-search":"stockSearch","ema-filter":"stockEmaFilter","stock-sort":"stockKey","pool":"stockRowLimit","watchlist-theme-search":"themeSelectorSearch"};
      Object.keys(fields).forEach(function (id) { if ($(id) && state[fields[id]] !== undefined) $(id).value = state[fields[id]]; });
      render();
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
    const marketWarnings = (data.context || []).filter((row) => [21, 50].some((period) => row.index_breadth?.[String(period)]?.status !== "valid")).map((row) => row.ticker + " breadth unavailable");
    $("status").textContent = marketWarnings.join(" · ");
    $("cards").innerHTML = data.context.map((row) =>
      '<article class="market-card"><div class="market-card-head"><div><div class="market-ticker">' + esc(row.ticker) + '</div><div class="market-title-sub">' +
      (row.ticker === "SPY" ? "S&P 500" : row.ticker === "QQQ" ? "Nasdaq-100" : "Russell 2000 proxy") +
      '</div></div><div>' + spark(row.history, "close", "Retrieved market price") .replace('class="spark"', 'class="market-chart"') +
      '</div></div><div class="market-price-row"><span class="price">' + money(row.price_close) + '</span><span class="market-daily" title="Latest regular-session change"><small>1D</small>' + pct(row.daily_change) + '</span><div class="market-returns">' +
      [["5", "1W"], ["21", "1M"], ["63", "3M"]].map((window) => '<span><small>' + window[1] + '</small>' + pct(row.returns[window[0]]?.value) + '</span>').join("") +
      '</div></div>' + conditions(row) + '<p class="market-observation">Data ' + esc(row.price_session_date || data.session_date || "unavailable") + (row.price_retrieved_at_hkt_display ? ' · Retrieved ' + esc(row.price_retrieved_at_hkt_display) : "") + '</p></article>'
    ).join("");
    $("volatility-card").innerHTML = (data.volatility_context || []).map(function (item) {
      const badge = item.source_status && item.source_status !== "available" ? '<span class="source-state source-missing">' + esc(item.source_status) + '</span>' : '';
      const percentile = finite(item.trailing_1y_percentile) ? 'Higher than ' + item.trailing_1y_percentile.toFixed(1) + '% of observations in the last ' + item.trailing_1y_observations + ' sessions.' : '1-year percentile unavailable.';
      const summary = item.vix_direction_summary || 'Volatility direction is mixed across the displayed periods.';
      return '<article class="market-card volatility-card"><div class="market-card-head"><div><div class="market-ticker">VIX</div><div class="market-title-sub">CBOE Volatility Index</div></div>' + badge + '</div>' +
        '<div class="vix-grid"><div><div class="price">' + (finite(item.level) ? item.level.toFixed(2) : "Unavailable") + '</div><div class="market-title-sub">1-year percentile ' + (finite(item.trailing_1y_percentile) ? item.trailing_1y_percentile.toFixed(1) : "Unavailable") + '</div></div>' +
        '<div class="vix-spark">' + spark(item.history, "close", "VIX closes") + '</div><div class="market-returns">' + vixChange("Today", item.daily_change, item.vix_direction_1d, item.source_reason) + vixChange("1 week", item.return5, item.vix_direction_5d, item.source_reason) + vixChange("1 month", item.return21, item.vix_direction_21d, item.source_reason) + '</div></div>' +
        '<p class="vix-context">' + esc(percentile) + '<br>' + esc(summary) + '</p><p class="market-observation">Data ' + esc(item.observation_date || "unavailable") + (item.retrieved_at_hkt_display ? ' · Retrieved ' + esc(item.retrieved_at_hkt_display) : "") + (item.source_reason ? ' · ' + esc(item.source_reason) : "") + '</p></article>';
    }).join("") || '<article class="market-card volatility-card"><div class="market-ticker">VIX</div><p class="warning">Volatility observation unavailable.</p></article>';
    var metrics = {
      rank_current: "Current rank",
      rank_t_minus_5: "Rank 5 sessions ago",
      rank_change_5: "5-session rank change",
      theme_score: "Theme Score",
      current_strength_score: "Current",
      medium_strength_score: "Medium",
      excess21: "1M vs SPY",
      excess63: "3M vs SPY",
      etf_breadth21_pct: "EMA21 breadth",
      etf_breadth50_pct: "EMA50 breadth",
      return5: "5-session return",
      return21: "21-session return",
      return63: "63-session return",
      price_close: "Price",
      adv30_usd: "ADV$30",
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
      const capacity = Number(data.settings?.watchlist_capacity || 20);
      const defaultCount = Number(data.settings?.watchlist_default_limit || Math.min(15, capacity));
      return '<label>Search <input id="stock-search" placeholder="Ticker or company"></label>' +
        '<label>Sort by <select id="stock-sort">' + options([["excess21","1M vs ETF"],["excess63","3M vs ETF"],["return5","5-session return"],["return21","21-session return"],["return63","63-session return"],["adv30_usd","ADV$30"],["price_close","Price"]]) +
        '</select></label><button id="stock-direction" type="button"></button>' +
        '<label>EMA <select id="ema-filter"><option value="all">All</option><option value="above21">Above EMA21</option><option value="below21">At/below EMA21</option><option value="above50">Above EMA50</option><option value="below50">At/below EMA50</option></select></label>' +
        '<label>Rows <select id="pool">' + [defaultCount, capacity].filter((value, index, list) => list.indexOf(value) === index).map((value) => '<option value="' + value + '">' + value + ' stocks</option>').join("") + '</select></label>';
    }
    $("theme-controls").innerHTML = '<label>Search <input id="theme-search" placeholder="Sector, theme or ETF"></label>' +
      '<label>Type <select id="theme-type"><option>All</option><option>Sector</option><option>Theme</option></select></label>' +
      '<label>State <select id="theme-state"><option>All</option><option>Leading</option><option>Improving</option><option>Fading</option><option>Lagging</option></select></label>' +
      '<label>Sort by <select id="theme-sort">' + options(Object.entries(metrics).filter(([key]) => !["return5","return21","return63","price_close","adv30_usd","name"].includes(key))) + '</select></label>' +
      '<button id="theme-direction" type="button"></button>';
    $("stock-controls").innerHTML = stockControls();
    $("theme-search").value = state.themeSearch || "";
    $("theme-type").value = state.themeType;
    $("theme-state").value = state.themeState;
    $("theme-sort").value = state.themeKey;
    $("stock-search").value = state.stockSearch || "";
    $("stock-sort").value = state.stockKey;
    $("ema-filter").value = state.stockEmaFilter || "all";
    $("pool").value = state.stockRowLimit || String(data.settings?.watchlist_default_limit || 15);
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
    $("pool").onchange = function () { state.stockRowLimit = this.value; render(); persistView(); };
    $("watchlist-theme-search").addEventListener("input", function () { state.themeSelectorSearch = this.value; renderThemeSelector(); persistView(); });
    function filtered(rows, p) {
      if (p === "theme") {
        const query = $("theme-search").value.trim().toLowerCase();
        return rows.filter(function (row) {
          const matchesText = !query || [row.name, row.anchor, row.id].some((v) => String(v || "").toLowerCase().includes(query));
          const type = row.level === "Sector" ? "Sector" : "Theme";
          const matchesType = state.themeType === "All" || type === state.themeType;
          const matchesState = state.themeState === "All" || row.theme_state === state.themeState;
          return matchesText && matchesType && matchesState;
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
              return '<th><div class="th-content">' + label + (c[3] ? infoControl(c[3]) : '') + '</div></th>';
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
      return '<span class="state-tag state-' + themeStateType(value) + '" aria-label="' + esc(value || "State unavailable") + ': ' + esc(help) + '">' + esc(value || "—") + "</span>";
    }
    function themeBreadthCell(row, period) {
      const metric = row.holdings_breadth?.[String(period)];
      const value = row["etf_breadth" + period + "_pct"];
      if (!metric || !finite(value) || metric.status !== "valid") {
        const count = metric && finite(metric.valid_count) && finite(metric.eligible_count) ? metric.valid_count + '/' + metric.eligible_count + ' holdings' : 'counts unavailable';
        const reason = metric?.reason || row["breadth_unavailable_reason_" + period] || "Holdings breadth is unavailable";
        const label = "Breadth unavailable · " + count + " · " + reason;
        return '<span class="breadth-unavailable-cell" title="' + esc(label) + '" aria-label="' + esc(label) + '">N/A</span>';
      }
      return '<span title="Holdings as of ' + esc(metric.as_of || "unknown") + '">' + value.toFixed(1) + '% <small>(' + metric.above_count + '/' + metric.valid_count + ')</small></span>';
    }
    function themeBreadthChangeCell(row, period) {
      const value = row["breadth" + period + "_change_5_pp"];
      const field = row.field_status?.["breadth" + period + "_change_5_pp"];
      return finite(value) ? '<span class="' + (value > 0 ? "positive" : value < 0 ? "negative" : "") + '">' + (value > 0 ? "+" : "") + value.toFixed(1) + ' pp</span>' : '<span title="' + esc(field?.reason || "Both current and prior breadth must be valid") + '">—</span>';
    }
    function rankChangeCell(row) {
      const value = row.rank_change_5;
      return finite(value) ? '<span class="' + (value > 0 ? "positive" : value < 0 ? "negative" : "") + '">' + (value > 0 ? "+" : "") + value.toFixed(value % 1 ? 1 : 0) + '</span>' : '<span title="' + esc(row.historical_rank_reason || "Historical ranking unavailable") + '">—</span>';
    }
    function breadthSummary(row, period) {
      const metric = row.holdings_breadth?.[String(period)];
      const change = row["breadth" + period + "_change_5_pp"];
      if (!metric || metric.status !== "valid" || !finite(row["etf_breadth" + period + "_pct"])) {
        const count = metric && finite(metric.valid_count) && finite(metric.eligible_count) ? metric.valid_count + "/" + metric.eligible_count + " holdings" : "counts unavailable";
        return "Breadth unavailable (" + count + ")";
      }
      return row["etf_breadth" + period + "_pct"].toFixed(1) + "%" + (finite(change) ? " · " + (change > 0 ? "+" : "") + change.toFixed(1) + " pp over 5 sessions" : " · 5-session change unavailable");
    }
    function select(id) {
      state.themeNavigationOrder = visibleThemes.map((row) => row.id);
      state.theme = id;
      showPage("watchlist", { push: true });
      render();
      replaceHistoryState();
    }
    var visible = [];
    var visibleThemes = [];
    function render() {
      setDirectionButton($("stock-direction"), state.stockDir);
      setDirectionButton($("theme-direction"), state.themeDir);
      var all = sortRows(data.themes || [], state.themeKey, state.themeDir).map((row) => Object.assign({}, row, { display_rank: row.global_rank }));
      visibleThemes = filtered(all, "theme");
      renderThemeSelector();
      const breadthUnavailable = visibleThemes.filter((row) => row.breadth_status_21 !== "valid" || row.breadth_status_50 !== "valid").length;
      $("theme-count").textContent = visibleThemes.length + " of " + all.length + " exposures" + (breadthUnavailable ? " · " + breadthUnavailable + " with breadth unavailable" : "");
      head("theme", [
        ["#", "rank_current", null, null, "Current rank"], ["Type", null, null, null, "Exposure type"], ["Name", "name", null, null, "Sector or theme name"], ["ETF", null, null, null, "Anchor ETF"], ["State", "theme_state", null, "state"],
        ["Score", "theme_score", null, "theme_score", "Theme Score"], ["Now", "current_strength_score", null, "current_strength_score", "Current strength"], ["Med", "medium_strength_score", null, "medium_strength_score", "Medium strength"],
        ["1M", "return21", null, null, "21-session return"], ["1M−SPY", "excess21", null, "excess21", "21-session excess return vs SPY"], ["3M", "return63", null, null, "63-session return"], ["3M−SPY", "excess63", null, "excess63", "63-session excess return vs SPY"],
        ["EMA21", "etf_breadth21_pct", null, "etf_breadth21_pct", "Holdings above EMA21"], ["Δ5D", null, null, null, "EMA21 breadth change over five sessions"], ["EMA50", "etf_breadth50_pct", null, "etf_breadth50_pct", "Holdings above EMA50"], ["Δ5D", null, null, null, "EMA50 breadth change over five sessions"], ["Rk−5D", null, null, null, "Rank five sessions ago"], ["Δ", null, null, null, "Rank change over five sessions"], ["Facts", null, null, null, "Facts and status"],
      ]);
      $("theme-body").innerHTML = visibleThemes.map(function (row) {
        const type = row.level === "Sector" ? "Sector" : "Theme";
        const details = [
          "ETF 5/21/63-session returns: " + pct(valueAt(row, "return5")) + " / " + pct(valueAt(row, "return21")) + " / " + pct(valueAt(row, "return63")),
          "ETF close vs EMA21/50: " + ema(row, 21) + " / " + ema(row, 50),
          "Holdings effective date: " + (row.holdings_asof || "unavailable"),
          "Current rank " + (row.rank_current ?? row.global_rank) + "; rank five sessions ago " + (row.rank_t_minus_5 ?? "unavailable") + "; rank change " + (finite(row.rank_change_5) ? row.rank_change_5 : row.historical_rank_reason || "unavailable"),
          "Historical rank peers: " + (row.historical_rank_peer_count ?? 0) + "; session " + (row.historical_rank_session || "unavailable"),
          "EMA21 breadth five-session change: " + (finite(row.breadth21_change_5_pp) ? row.breadth21_change_5_pp + " pp" : row.field_status?.breadth21_change_5_pp?.reason || "unavailable"),
        ].join("<br>");
        return '<tr data-theme="' + esc(row.id) + '" class="' + (row.id === state.theme ? "active" : "") + '">' +
          '<td>' + (row.display_rank || "—") + '</td><td>' + type + '</td><td><button class="theme-select">' + esc(row.name) + '</button></td><td>' +
          (row.chart_url ? '<a href="' + esc(row.chart_url) + '" target="_blank" rel="noopener noreferrer">' + esc(row.anchor) + '</a>' : esc(row.anchor)) +
          '</td><td>' + stateBadge(row.theme_state) + '</td><td>' + score(row, "theme_score") + '</td><td>' + score(row, "current_strength_score") + '</td><td>' + score(row, "medium_strength_score") + '</td>' +
          '<td>' + pct(valueAt(row, "return21")) + '</td><td>' + pct(valueAt(row, "excess21"), true) + '</td><td>' + pct(valueAt(row, "return63")) + '</td><td>' + pct(valueAt(row, "excess63"), true) + '</td>' +
          '<td>' + themeBreadthCell(row, 21) + '</td><td>' + themeBreadthChangeCell(row, 21) + '</td>' +
          '<td>' + themeBreadthCell(row, 50) + '</td><td>' + themeBreadthChangeCell(row, 50) + '</td>' +
          '<td title="' + esc(row.historical_rank_reason || "Recomputed using current eligible ETF peers") + '">' + (row.rank_t_minus_5 ?? "—") + '</td><td>' + rankChangeCell(row) + '</td>' +
          '<td><details><summary>Facts &amp; status</summary><div class="stock-details">' + details + '</div></details></td></tr>';
      }).join("") || '<tr><td colspan="19">No eligible ETF exposures are available in this snapshot.</td></tr>';
      $("theme-body").querySelectorAll("tr[data-theme]").forEach(function (tr) {
        tr.addEventListener("click", function (event) {
          if (!event.target.closest("a, details, summary")) select(tr.dataset.theme);
        });
      });
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
      $("active-name").textContent = "Watchlist · " + selected.name + " / " + selected.anchor;
      const priorRank = finite(selected.rank_t_minus_5) ? selected.rank_t_minus_5.toFixed(selected.rank_t_minus_5 % 1 ? 1 : 0) : "unavailable";
      const rankMove = finite(selected.rank_change_5) ? '<span class="' + (selected.rank_change_5 > 0 ? "positive" : selected.rank_change_5 < 0 ? "negative" : "") + '">' + (selected.rank_change_5 > 0 ? "+" : "") + selected.rank_change_5.toFixed(selected.rank_change_5 % 1 ? 1 : 0) + '</span>' : '<span title="' + esc(selected.historical_rank_reason || "Historical ranking unavailable") + '">unavailable</span>';
      $("active-summary").innerHTML = '<div class="summary-scores">' + stateBadge(selected.theme_state) + ' ' + score(selected, "theme_score") + ' ' + score(selected, "current_strength_score") + ' ' + score(selected, "medium_strength_score") + '</div>' +
        '<div class="summary-returns"><span>1M return ' + pct(valueAt(selected, "return21")) + '</span><span>1M vs SPY ' + pct(valueAt(selected, "excess21"), true) + '</span><span>3M return ' + pct(valueAt(selected, "return63")) + '</span><span>3M vs SPY ' + pct(valueAt(selected, "excess63"), true) + '</span></div>' +
        '<div class="summary-rank">Rank ' + (selected.rank_current ?? selected.global_rank ?? "unavailable") + ' · 5 sessions ago ' + priorRank + ' · change ' + rankMove + ' · ' + (selected.historical_rank_peer_count ?? 0) + ' peers</div>' +
        '<div class="summary-breadth">Holdings breadth — EMA21 ' + breadthSummary(selected, 21) + ' · EMA50 ' + breadthSummary(selected, 50) + '</div>' +
        '<div class="rs-spark-row"><span>63-session ETF / SPY</span>' + spark(selected.relative_strength_series, "ratio", "ETF to SPY adjusted-close ratio") + '</div>';
      var pool = $("pool").value;
      var base = limitSelection(selected.selected || [], Number(pool));
      base = base.map((row) => Object.assign({}, row, { theme_id: selected.id, theme_name: selected.name, generated_at: data.dashboard_generated_at || data.generated_at }));
      visible = filtered(sortRows(base, state.stockKey, state.stockDir).map((row) => Object.assign({}, row, { display_rank: row.selection_slot })), "stock");
      var hasCuratedList = base.length > 0;
      $("stock-controls").hidden = !hasCuratedList;
      $("stock-table-wrap").hidden = !hasCuratedList;
      $("stock-exports").hidden = !hasCuratedList;
      $("watchlist-message").hidden = hasCuratedList;
      if (!hasCuratedList) {
        $("watchlist-message").textContent = "No curated stock drilldown is available for this theme.";
        $("coverage").textContent = "";
        visible = [];
        $("csv").disabled = true;
        $("tv").disabled = true;
      } else {
        const capacity = Number(data.settings?.watchlist_capacity || 20);
        $("coverage").textContent = base.length + " of " + capacity + " stocks";
      }
      head("stock", [["#", null, null, null, "Visible rank"],["Ticker / company", null, null, null, "Ticker and company name"],["Price","price_close",null,null,"Latest close"],["5D %","return5",null,null,"Five-session return"],["1M %","return21",null,null,"21-session return"],["3M %","return63",null,null,"63-session return"],["1M−ETF","excess21",null,null,"21-session excess return vs anchor ETF, percentage points"],["3M−ETF","excess63",null,null,"63-session excess return vs anchor ETF, percentage points"],["EMA21",null,null,null,"Close relative to EMA21"],["EMA50",null,null,null,"Close relative to EMA50"],["Core / Related",null,null,null,"Membership relationship"],["ADV$30","adv30_usd",null,null,"30-session average daily dollar volume"],["Chart",null,null,null,"Open verified ticker chart"]]);
      $("stock-body").innerHTML = visible.map(function (row) {
        const exchange = String(row.exchange || "").toUpperCase();
        const prefix = exchange.startsWith("NASDAQ") ? "NASDAQ" : exchange.startsWith("NYSE") ? "NYSE" : null;
        const url = prefix ? "https://www.tradingview.com/chart/?symbol=" + encodeURIComponent(prefix + ":" + row.ticker) : null;
        const rationale = row.membership_rationale || row.evidence_note || "Business relevance rationale recorded in the membership source.";
        return '<tr><td>' + (row.display_rank || "—") + '</td><td><b>' + esc(row.ticker) + '</b><span class="company" title="' + esc(row.company) + '">' + esc(row.company) + '</span><details><summary aria-label="Business rationale">Info</summary><div class="stock-details">' + esc(rationale) + '<br>' + esc(row.membership_source || row.evidence?.url || "") + '</div></details></td>' +
          '<td>' + money(row.price_close) + '</td>' + ["return5","return21","return63","excess21","excess63"].map((key) => '<td>' + pct(valueAt(row,key), key.startsWith("excess")) + '</td>').join("") +
          '<td>' + ema(row,21) + '</td><td>' + ema(row,50) + '</td><td>' + esc(row.membership_tag || "—") + '</td><td>' + money(row.adv30_usd,true) + '</td><td>' + (url ? '<a target="_blank" rel="noopener noreferrer" href="' + esc(url) + '">Open</a>' : missing) + '</td></tr>';
      }).join("") || (hasCuratedList ? '<tr><td colspan="13">No stocks match these filters.</td></tr>' : "");
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
      var result = tradingViewExport(visible);
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
  };
});
