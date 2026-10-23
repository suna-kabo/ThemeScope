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

  function themeRowsToCsv(rows, session) {
    var columns = ["rank", "type", "name", "anchor_etf", "state", "theme_score", "current_strength", "medium_strength", "return21", "excess21_pp", "return63", "excess63_pp", "holdings_breadth21_pct", "breadth21_above", "breadth21_valid", "holdings_breadth50_pct", "breadth50_above", "breadth50_valid", "holdings_asof", "score_status", "score_reason", "session_date"];
    var lines = [columns.map(csvEscape).join(",")];
    rows.forEach(function (row) {
      var b21 = row.holdings_breadth && row.holdings_breadth["21"] || {};
      var b50 = row.holdings_breadth && row.holdings_breadth["50"] || {};
      var values = [row.display_rank, row.level === "Sector" ? "Sector" : "Theme", row.name,
        row.anchor, row.theme_state, row.theme_score, row.current_strength_score,
        row.medium_strength_score, valueAt(row, "return21"),
        finiteNumber(valueAt(row, "excess21")) ? valueAt(row, "excess21") * 100 : null,
        valueAt(row, "return63"), finiteNumber(valueAt(row, "excess63")) ? valueAt(row, "excess63") * 100 : null,
        row.etf_breadth21_pct, b21.above_count, b21.valid_count, row.etf_breadth50_pct,
        b50.above_count, b50.valid_count, row.holdings_asof,
        row.field_status?.theme_score?.status, row.field_status?.theme_score?.reason, session];
      lines.push(values.map(csvEscape).join(","));
    });
    return lines.join("\r\n");
  }

  function rowsToCsv(rows) {
    var header = [
      "theme",
      "theme_id",
      "session_date",
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
    var missing =
      '<span title="Input unavailable; see diagnostic export">—</span>';
    var scoreConfig = data.score_methodology || {};
    var currentWeights = scoreConfig.current_strength_weights || {};
    var mediumWeights = scoreConfig.medium_strength_weights || {};
    var finalWeights = scoreConfig.theme_score_weights || {};
    var weightText = function (part, key) {
      var value = part[key];
      return typeof value === "number" ? (value * 100).toFixed(0) + "%" : "unavailable";
    };
    $("score-method-description").textContent =
      "CurrentStrength = " + weightText(currentWeights, "excess21_percentile") + " 21-session excess-return percentile + " + weightText(currentWeights, "breadth21") + " holdings breadth above EMA21. MediumStrength = " +
      weightText(mediumWeights, "excess63_percentile") + " 63-session excess-return percentile + " + weightText(mediumWeights, "breadth50") + " holdings breadth above EMA50. ThemeScore = " +
      weightText(finalWeights, "current_strength") + " CurrentStrength + " + weightText(finalWeights, "medium_strength") + " MediumStrength. These fixed weights support manual review; they are not a validated trading model.";
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
      const m = row.field_status?.[key];
      return finite(row[key])
        ? '<span title="Fixed configured browsing convention">' +
            row[key].toFixed(1) +
            "</span>"
        : '<span title="Score unavailable; see the run report or snapshot diagnostics">—</span>';
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
      if (!m || !finite(m.value) || m.status !== "valid")
        return '<span class="muted" title="' + esc(m?.reason || "Breadth is unavailable or fails its configured completeness rule") + '">Insufficient data</span>';
      return (
        '<div class="breadth-row"><b class="breadth-value">' +
        m.value.toFixed(1) +
        '%</b><span class="breadth-count">' +
        m.above_count +
        " of " +
        m.valid_count +
        " above</span></div><div class=\"meter\"><i style=\"width:" +
        Math.max(0, Math.min(100, m.value)) +
        '%\"></i></div>'
      );
    }
    function conditionCard(row, period) {
      const label = "EMA" + period;
      const above = row["above_ema" + period];
      const movingAverage = row["ema" + period];
      const relationship = above === true ? "Above" : above === false ? "Below/At" : "Unavailable";
      const color = above === true ? "positive" : above === false ? "negative" : "muted";
      return (
        '<div class="condition-box"><small>' + label +
        '</small><b class="ema-fact ' + color + '">' + relationship +
        '</b><span class="coverage-line">EMA value ' +
        (finite(movingAverage) ? money(movingAverage) : "Unavailable") +
        "</span></div>"
      );
    }
    function ema(row, period) {
      let fact = row["above_ema" + period];
      if (
        fact === undefined &&
        finite(row.price_close) &&
        finite(row["ema" + period])
      )
        fact = row.price_close > row["ema" + period];
      return fact === true
        ? '<span class="positive">Above</span>'
        : fact === false
          ? '<span class="negative">At/below</span>'
          : missing;
    }
    function conditions(row) {
      return (
        '<div class="market-indicators"><div class="indicator-box"><div class="indicator-label"><span>Above EMA21</span><span class="ema-pill ' +
        (row.above_ema21 === true
          ? "ema-above"
          : row.above_ema21 === false
            ? "ema-below"
            : "") +
        '">' +
        (row.above_ema21 === true
          ? "Price above"
          : row.above_ema21 === false
            ? "Price at/below"
            : "Unavailable") +
        '</span></div>' +
        marketBreadth(row, 21) +
        '</div><div class="indicator-box"><div class="indicator-label"><span>Above EMA50</span><span class="ema-pill ' +
        (row.above_ema50 === true
          ? "ema-above"
          : row.above_ema50 === false
            ? "ema-below"
            : "") +
        '">' +
        (row.above_ema50 === true
          ? "Price above"
          : row.above_ema50 === false
            ? "Price at/below"
            : "Unavailable") +
        '</span></div>' +
        marketBreadth(row, 50) +
        '</div></div><div class="condition-row">' +
        conditionCard(row, 21) +
        conditionCard(row, 50) +
        '</div><p class="coverage-line">Constituent list observed ' +
        esc(row.index_constituent_asof || "date unavailable") +
        "; membership is current, not point-in-time.</p>"
      );
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
    function spark(history) {
      var values = (history || []).filter((r) => finite(r.close));
      if (values.length < 2) return missing;
      var lo = Math.min(...values.map((r) => r.close)),
        hi = Math.max(...values.map((r) => r.close)),
        span = hi - lo || 1;
      var segments = [],
        current = [];
      (history || []).forEach(function (r, i) {
        if (!finite(r.close)) {
          if (current.length) segments.push(current.join(" "));
          current = [];
        } else
          current.push(
            ((i / Math.max(1, history.length - 1)) * 108 + 1).toFixed(1) +
              "," +
              (32 - ((r.close - lo) / span) * 30).toFixed(1),
          );
      });
      if (current.length) segments.push(current.join(" "));
      return (
        '<svg class="spark" viewBox="0 0 110 34" role="img" aria-label="Retrieved split-adjusted closing prices"><title>' +
        esc(values[0].date + " to " + values[values.length - 1].date) +
        "</title>" +
        segments
          .map(
            (s) =>
              '<polyline points="' +
              s +
              '" fill="none" stroke="currentColor" stroke-width="1.5"/>',
          )
          .join("") +
        "</svg>"
      );
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
    function showPage(id, updateHash) {
      if (!pageIds.includes(id)) id = "market";
      document.querySelectorAll(".page").forEach(function (page) {
        page.hidden = page.id !== id;
      });
      document.querySelectorAll(".side-nav [data-page]").forEach(function (link) {
        var active = link.dataset.page === id;
        link.classList.toggle("active", active);
        if (active) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
      if (updateHash && location.hash !== "#" + id) {
        try {
          history.replaceState(null, "", "#" + id);
        } catch (e) {}
      }
      window.scrollTo(0, 0);
    }
    document.querySelectorAll(".side-nav [data-page]").forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        showPage(link.dataset.page, true);
      });
    });
    window.addEventListener("hashchange", function () {
      showPage(location.hash.slice(1), false);
    });
    $("date").textContent = data.session_date || "Unavailable";
    $("sidebar-date").textContent = data.session_date || "Unavailable";
    $("generated").textContent =
      "Snapshot created " +
      (data.generated_at || "unknown") +
      (data.last_source_retrieved_at ? " · Last price retrieval " + data.last_source_retrieved_at : "") +
      (data.imported_at
        ? " · Imported " + data.imported_at + " (original data date retained)"
        : "");
    if (
      !data.session_date ||
      !["SPY", "QQQ"].every((t) =>
        (data.context || []).some(
          (r) => r.ticker === t && finite(r.price_close),
        ),
      )
    ) {
      $("status").textContent =
        "Market data unavailable: " +
        (Object.values(data.sources?.source_errors?.charts || {})
          .slice(0, 1)
          .join(" ") || "Required dated SPY/QQQ prices are missing.") +
        " Run the generation script; reopening this file cannot retry collection.";
      document.querySelectorAll("section").forEach((s) => (s.hidden = true));
      return;
    }
    showPage(location.hash.slice(1) || "market", false);
    const eligibleAnchors = (data.themes || []).length;
    const registryRecords = (data.registry_diagnostics || []).length;
    $("status").textContent =
      "v6 · End-of-day snapshot · " + eligibleAnchors + " eligible ETF anchors from " +
      registryRecords + " registry records. Candidate source gaps are listed in the audit. " +
      (data.sources?.partial ? "Some source requests also failed. " : "") +
      "Opening this file makes no market-data requests.";
    $("cards").innerHTML = data.context
      .map(
        (r) =>
          '<article class="market-card"><div class="market-card-head"><div><div class="market-ticker">' +
          esc(r.ticker) +
          '</div><div class="market-title-sub">' +
          (r.ticker === "SPY"
            ? "S&P 500 · broad U.S. large-cap market"
            : "Nasdaq-100 · growth-heavy market context") +
          '</div></div><div>' +
          spark(r.history).replace('class="spark"', 'class="market-chart"') +
          '</div></div><div class="market-price-row"><span class="price">' +
          money(r.price_close) +
          '</span><span title="Latest regular-session change">' +
          pct(r.daily_change) +
          '</span><div class="market-returns">' +
          [
            ["5", "1W"],
            ["21", "1M"],
            ["63", "3M"],
          ]
            .map(
              (w) =>
                '<span><small title="Total return over 5 / 21 / 63 trading sessions, using adjusted close">' +
                w[1] +
                "</small>" +
                pct(r.returns[w[0]]?.value) +
                "</span>",
            )
            .join("") +
          "</div></div>" +
          conditions(r) +
          "</article>",
      )
      .join("");
    var metrics = {
      theme_score: "Theme Score",
      current_strength_score: "Current",
      medium_strength_score: "Medium",
      excess21: "1M vs SPY",
      excess63: "3M vs SPY",
      etf_breadth21_pct: "Above EMA21",
      etf_breadth50_pct: "Above EMA50",
      return5: "5-session return",
      return21: "21-session return",
      return63: "63-session return",
      price_close: "Price",
      adv30_usd: "ADV$30",
      name: "Name",
    };
    var initialTheme = data.themes.find((t) => (t.selected || []).length) || data.themes[0];
    var state = {
      theme: initialTheme?.id,
      themeKey: "theme_score",
      themeDir: "desc",
      stockKey: "excess21",
      stockDir: "desc",
      themeType: "All",
      themeState: "All",
    };
    function options(list) {
      return list.map((v) => '<option value="' + esc(v[0]) + '">' + esc(v[1]) + "</option>").join("");
    }
    function stockControls() {
      return '<label>Search <input id="stock-search" placeholder="Ticker or company"></label>' +
        '<label>Sort by <select id="stock-sort">' + options([["excess21","1M vs ETF"],["excess63","3M vs ETF"],["return5","5-session return"],["return21","21-session return"],["return63","63-session return"],["adv30_usd","ADV$30"],["price_close","Price"]]) +
        '</select></label><button id="stock-direction">Descending ↓</button>' +
        '<label>EMA <select id="ema-filter"><option value="all">All</option><option value="above21">Above EMA21</option><option value="below21">At/below EMA21</option><option value="above50">Above EMA50</option><option value="below50">At/below EMA50</option></select></label>' +
        '<label>Rows <select id="pool"><option value="15">15 rows</option><option value="20">20 rows</option></select></label>';
    }
    $("theme-controls").innerHTML = '<label>Search <input id="theme-search" placeholder="Sector, theme or ETF"></label>' +
      '<label>Type <select id="theme-type"><option>All</option><option>Sector</option><option>Theme</option></select></label>' +
      '<label>State <select id="theme-state"><option>All</option><option>Leading</option><option>Improving</option><option>Fading</option><option>Lagging</option></select></label>' +
      '<label>Sort by <select id="theme-sort">' + options(Object.entries(metrics).filter(([key]) => !["return5","return21","return63","price_close","adv30_usd","name"].includes(key))) + '</select></label>' +
      '<button id="theme-direction">Descending ↓</button>';
    $("stock-controls").innerHTML = stockControls();
    $("theme-sort").value = state.themeKey;
    $("theme-sort").onchange = function () { state.themeKey = this.value; render(); };
    $("theme-direction").onclick = function () { state.themeDir = state.themeDir === "desc" ? "asc" : "desc"; render(); };
    $("theme-search").addEventListener("input", render);
    $("theme-type").onchange = function () { state.themeType = this.value; render(); };
    $("theme-state").onchange = function () { state.themeState = this.value; render(); };
    $("stock-sort").value = state.stockKey;
    $("stock-sort").onchange = function () { state.stockKey = this.value; render(); };
    $("stock-direction").onclick = function () { state.stockDir = state.stockDir === "desc" ? "asc" : "desc"; render(); };
    $("stock-search").addEventListener("input", render);
    $("ema-filter").onchange = render;
    $("pool").onchange = render;
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

    function head(p, columns) {
      $(p + "-head").innerHTML =
        "<tr>" +
        columns
          .map(
            (c) =>
              "<th>" +
              (c[1]
                ? '<button data-sort="' +
                  c[1] +
                  '" title="' +
                  esc(
                    c[2] || "Sort numeric values; missing values remain last",
                  ) +
                  '">' +
                  c[0] +
                  (state[p + "Key"] === c[1]
                    ? state[p + "Dir"] === "desc"
                      ? " ↓"
                      : " ↑"
                    : "") +
                  "</button>"
                : c[0]) +
              "</th>",
          )
          .join("") +
        "</tr>";
      $(p + "-head")
        .querySelectorAll("button")
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
          : "Cross-sectional state from CurrentStrength and MediumStrength.";
      return '<span class="state-tag state-' + themeStateType(value) + '" title="' + esc(help) + '">' + esc(value || "—") + "</span>";
    }
    function themeBreadthCell(row, period) {
      const metric = row.holdings_breadth?.[String(period)];
      const value = row["etf_breadth" + period + "_pct"];
      if (!metric || !finite(value) || metric.status !== "valid")
        return '<span title="' + esc(metric?.reason || "Holdings breadth is unavailable or fails its configured sample, freshness, or completeness rule") + '">—</span>';
      return '<span title="Equal-company holdings participation; ' + esc(metric.above_count + '/' + metric.valid_count + ' valid; holdings as of ' + (metric.as_of || "unknown")) + '">' + value.toFixed(1) + '% <small>(' + metric.above_count + '/' + metric.valid_count + ')</small></span>';
    }
    function select(id) {
      state.theme = id;
      showPage("watchlist", true);
      render();
    }
    var visible = [];
    var visibleThemes = [];
    function render() {
      $("stock-direction").textContent = state.stockDir === "desc" ? "Descending ↓" : "Ascending ↑";
      $("theme-direction").textContent = state.themeDir === "desc" ? "Descending ↓" : "Ascending ↑";
      var all = sortRows(data.themes || [], state.themeKey, state.themeDir).map((row) => Object.assign({}, row, { display_rank: row.global_rank }));
      visibleThemes = filtered(all, "theme");
      $("theme-count").textContent = visibleThemes.length + " / " + all.length + " eligible sector/theme ETFs shown · " + data.session_date;
      head("theme", [
        ["Rank"], ["Type"], ["Sector / Theme", "name"], ["ETF"], ["State"],
        ["Theme Score", "theme_score"], ["Current", "current_strength_score"], ["Medium", "medium_strength_score"],
        ["1M vs SPY", "excess21"], ["3M vs SPY", "excess63"], ["Above EMA21", "etf_breadth21_pct"], ["Above EMA50", "etf_breadth50_pct"], ["Details"],
      ]);
      $("theme-body").innerHTML = visibleThemes.map(function (row) {
        const type = row.level === "Sector" ? "Sector" : "Theme";
        const details = [
          "ETF 5/21/63-session returns: " + pct(valueAt(row, "return5")) + " / " + pct(valueAt(row, "return21")) + " / " + pct(valueAt(row, "return63")),
          "ETF close vs EMA21/50: " + ema(row, 21) + " / " + ema(row, 50),
          "Holdings effective date: " + (row.holdings_asof || "unavailable"),
          finite(row.theme_score) ? "Score components are valid for this session." : "Score unavailable; exact field reasons are in the snapshot and run report.",
        ].join("<br>");
        return '<tr data-theme="' + esc(row.id) + '" class="' + (row.id === state.theme ? "active" : "") + '">' +
          '<td>' + (row.display_rank || "—") + '</td><td>' + type + '</td><td><button class="theme-select">' + esc(row.name) + '</button></td><td>' +
          (row.chart_url ? '<a href="' + esc(row.chart_url) + '" target="_blank" rel="noopener noreferrer">' + esc(row.anchor) + ' ↗</a>' : esc(row.anchor)) +
          '</td><td>' + stateBadge(row.theme_state) + '</td><td>' + score(row, "theme_score") + '</td><td>' + score(row, "current_strength_score") + '</td><td>' + score(row, "medium_strength_score") + '</td>' +
          '<td>' + pct(valueAt(row, "excess21"), true) + '</td><td>' + pct(valueAt(row, "excess63"), true) + '</td>' +
          '<td>' + themeBreadthCell(row, 21) + '</td>' +
          '<td>' + themeBreadthCell(row, 50) + '</td>' +
          '<td><details><summary>Facts &amp; status</summary><div class="stock-details">' + details + '</div></details></td></tr>';
      }).join("") || '<tr><td colspan="13">No eligible anchor ETFs passed this run’s configured checks. Open the registry audit for candidate-specific reasons.</td></tr>';
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
        $("watchlist-message").textContent = "No curated stock drilldown is available because no eligible anchor ETF passed this run’s checks.";
        $("stock-controls").hidden = true;
        $("stock-exports").hidden = true;
        $("stock-basis").textContent = "";
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
      $("active-summary").innerHTML = "ETF 1M " + pct(valueAt(selected, "return21")) + " · 3M " + pct(valueAt(selected, "return63")) +
        " · ThemeScore " + score(selected, "theme_score") + " · Current " + score(selected, "current_strength_score") + " · Medium " + score(selected, "medium_strength_score") +
        " · " + stateBadge(selected.theme_state) + "<br>Anchor ETF holdings breadth: EMA21 " + breadth(selected, 21) + " · EMA50 " + breadth(selected, 50);
      var pool = $("pool").value;
      var base = limitSelection(selected.selected || [], Number(pool));
      base = base.map((row) => Object.assign({}, row, { theme_id: selected.id, theme_name: selected.name }));
      visible = filtered(sortRows(base, state.stockKey, state.stockDir).map((row) => Object.assign({}, row, { display_rank: row.selection_slot })), "stock");
      var hasCuratedList = base.length > 0;
      $("stock-controls").hidden = !hasCuratedList;
      $("stock-table-wrap").hidden = !hasCuratedList;
      $("stock-exports").hidden = !hasCuratedList;
      $("watchlist-message").hidden = hasCuratedList;
      if (!hasCuratedList) {
        $("watchlist-message").textContent = "No curated stock drilldown for this theme. The ETF remains available in the Sectors & Themes comparison.";
        $("stock-basis").textContent = "";
        $("coverage").textContent = "";
        visible = [];
        $("csv").disabled = true;
        $("tv").disabled = true;
      } else {
        $("stock-basis").textContent = visible.length + " / " + base.length + " shown · membership and selection are fixed for this snapshot; sorting does not refill the list.";
        $("coverage").textContent = "Selected list is a browsing convention with a 20-stock capacity and 15-row default; it is not a validated trading model.";
      }
      head("stock", [["Rank"],["Ticker / company"],["Price","price_close"],["5-session %","return5"],["21-session %","return21"],["63-session %","return63"],["21-session vs ETF (pp)","excess21"],["63-session vs ETF (pp)","excess63"],["EMA21"],["EMA50"],["Core / Related"],["ADV$30","adv30_usd"],["Chart"]]);
      $("stock-body").innerHTML = visible.map(function (row) {
        const exchange = String(row.exchange || "").toUpperCase();
        const prefix = exchange.startsWith("NASDAQ") ? "NASDAQ" : exchange.startsWith("NYSE") ? "NYSE" : null;
        const url = prefix ? "https://www.tradingview.com/chart/?symbol=" + encodeURIComponent(prefix + ":" + row.ticker) : null;
        const rationale = row.membership_rationale || row.evidence_note || "Business relevance rationale recorded in the membership source.";
        return '<tr><td>' + (row.display_rank || "—") + '</td><td><b>' + esc(row.ticker) + '</b><span class="company">' + esc(row.company) + '</span><details><summary>Rationale</summary><div class="stock-details">' + esc(rationale) + '<br>' + esc(row.membership_source || row.evidence?.url || "") + '</div></details></td>' +
          '<td>' + money(row.price_close) + '</td>' + ["return5","return21","return63","excess21","excess63"].map((key) => '<td>' + pct(valueAt(row,key), key.startsWith("excess")) + '</td>').join("") +
          '<td>' + ema(row,21) + '</td><td>' + ema(row,50) + '</td><td>' + esc(row.membership_tag || "—") + '</td><td>' + money(row.adv30_usd,true) + '</td><td>' + (url ? '<a target="_blank" rel="noopener noreferrer" href="' + esc(url) + '">Open ↗</a>' : missing) + '</td></tr>';
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
      download("themescope-visible-themes-" + data.session_date + ".csv", themeRowsToCsv(visibleThemes, data.session_date), "text/csv;charset=utf-8");
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
  };
});
