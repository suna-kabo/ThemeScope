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
        [row.ticker, row.company, row.theme_name, row.evidence_note].some(
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
        ? '<span title="Fixed v5 ranking convention">' +
            row[key].toFixed(1) +
            "</span>"
        : '<span title="' + esc(m?.reason || "Unavailable") + '">—</span>';
    }
    function breadth(row, period, index = false) {
      const m = (index ? row.index_breadth : row.holdings_breadth)?.[
        String(period)
      ];
      if (!m || m.value === null)
        return (
          '<span title="' +
          esc(m?.reason || "Constituent data unavailable") +
          '">—</span>'
        );
      return (
        '<span class="' +
        (m.status === "valid" ? "" : "warning") +
        '" title="' +
        esc(
          (m.reason || "Valid") +
            "; price coverage " +
            m.valid_count +
            "/" +
            m.eligible_count +
            "; holdings as of " +
            m.as_of,
        ) +
        '">' +
        m.value.toFixed(1) +
        "% <small>(" +
        m.above_count +
        "/" +
        m.valid_count +
        ") · " + (finite(m.coverage_pct) ? m.coverage_pct.toFixed(1) : "—") + "% coverage</small>" +
        (m.status === "valid" ? "" : " ⚠") +
        "</span>"
      );
    }
    function marketBreadth(row, period) {
      const m = row.index_breadth?.[String(period)];
      if (!m || !finite(m.value))
        return '<span class="muted" title="' + esc(m?.reason || "Constituent data unavailable") + '">Unavailable</span>';
      const coverage = finite(m.coverage_pct) ? m.coverage_pct.toFixed(1) : "—";
      return (
        '<div class="breadth-row"><b class="breadth-value">' +
        m.value.toFixed(1) +
        '%</b><span class="breadth-count">' +
        m.above_count +
        " of " +
        m.valid_count +
        " above</span></div><div class=\"meter\"><i style=\"width:" +
        Math.max(0, Math.min(100, m.value)) +
        '%\"></i></div><div class="coverage-line">Price coverage ' +
        coverage +
        "% · " +
        m.valid_count +
        "/" +
        m.eligible_count +
        " constituents have data</div>"
      );
    }
    function conditionType(text) {
      if (/^Broad .* weakness/.test(text || "")) return "weak";
      if (/^Broad .* strength/.test(text || "")) return "broad";
      if (/^Narrow /.test(text || "")) return "narrow";
      if (/^Internal strength/.test(text || "")) return "internal";
      return "unavailable";
    }
    function conditionCard(row, period) {
      const label = "EMA" + period;
      const condition = row["market_condition" + period] || "Unavailable";
      const type = conditionType(condition);
      const distance = row["ema" + period + "_distance"];
      const relation = !finite(distance)
        ? "Price vs " + label + " unavailable"
        : "Close " +
          (distance > 0 ? "above " : "at or below ") +
          label +
          " by " +
          Math.abs(distance * 100).toFixed(2) +
          "%";
      return (
        '<div class="condition-box condition-' +
        type +
        '"><small>' +
        (period === 21 ? "SHORT TERM" : "MEDIUM TERM") +
        " · " +
        label +
        '</small><span class="state-pill state-' +
        type +
        '">' +
        esc(condition) +
        '</span><span class="coverage-line">' +
        esc(relation) +
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
        '</div><p class="coverage-line">Index constituents observed ' +
        esc(row.index_constituent_asof || "date unavailable") +
        "</p>"
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
    var pageIds = ["market", "sectors", "industries", "themes", "watchlist"];
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
    $("status").textContent =
      "v5 · End-of-day snapshot · " +
      (data.sources?.partial
        ? "Core data verified; optional source gaps. "
        : "Core data retrieved. ") +
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
      theme_score: "ThemeScore",
      current_strength_score: "CurrentStrength",
      medium_strength_score: "MediumStrength",
      etf_breadth21_pct: "ETF breadth EMA21",
      etf_breadth50_pct: "ETF breadth EMA50",
      return5: "1W return",
      return21: "1M return",
      return63: "3M return",
      excess21: "1M excess",
      excess63: "3M excess",
      price_close: "Price",
      adv30_usd: "ADV$30",
    };
    var initialTheme =
      data.themes.find((t) => t.level !== "Sector" && (t.selected || []).length) ||
      data.themes.find((t) => t.level !== "Sector") ||
      data.themes[0];
    var state = {
      theme: initialTheme?.id,
      themeKey: "theme_score",
      themeDir: "desc",
      stockKey: "excess21",
      stockDir: "desc",
      sectorKey: "theme_score",
      sectorDir: "desc",
      industryKey: "median_return21_pct",
      industryDir: "desc",
    };
    function options(list) {
      return list
        .map(
          (v) => '<option value="' + esc(v[0]) + '">' + esc(v[1]) + "</option>",
        )
        .join("");
    }
    function controls(prefix, stock) {
      return (
        '<label>Search <input id="' +
        prefix +
        '-search" placeholder="' +
        (stock ? "Ticker or company" : "Theme or ETF") +
        '"></label><label>Sort by <select id="' +
        prefix +
        '-sort">' +
        options(
          Object.entries(metrics).filter(([k]) =>
            stock
              ? ![
                  "theme_score",
                  "current_strength_score",
                  "medium_strength_score",
                  "etf_breadth21_pct",
                  "etf_breadth50_pct",
                ].includes(k)
              : !["price_close", "adv30_usd"].includes(k),
          ),
        ) +
        '</select></label><button id="' +
        prefix +
        '-direction">Descending ↓</button><label>Trend <select id="' +
        prefix +
        '-trend">' +
        options(["All", "Uptrend", "Downtrend", "Mixed"].map((v) => [v, v])) +
        '</select></label><label>Relative state <select id="' +
        prefix +
        '-relative">' +
        options(
          ["All", "Outperforming", "Underperforming"].map((v) => [v, v]),
        ) +
        "</select></label>" +
        (stock
          ? '<label>Pool <select id="pool"><option value="15">Selected 15</option><option value="20">Selected 20</option><option value="all">All accepted eligible</option></select></label>'
          : "")
      );
    }
    $("theme-controls").innerHTML = controls("theme", false);
    $("stock-controls").innerHTML = controls("stock", true);
    ["theme", "stock"].forEach(function (p) {
      $(p + "-sort").value = p === "theme" ? "theme_score" : "excess21";
      $(p + "-sort").onchange = function () {
        state[p + "Key"] = this.value;
        render();
      };
      $(p + "-direction").onclick = function () {
        state[p + "Dir"] = state[p + "Dir"] === "desc" ? "asc" : "desc";
        render();
      };
      ["search", "trend", "relative"].forEach((k) =>
        $(p + "-" + k).addEventListener("input", render),
      );
    });
    $("theme-controls").insertAdjacentHTML(
      "beforeend",
      '<label>Level <select id="level"><option>All</option><option>Industry</option><option>Theme</option></select></label>',
    );
    $("level").onchange = render;
    $("industry-search").addEventListener("input", render);
    $("stock-controls").insertAdjacentHTML(
      "beforeend",
      '<label>EMA <select id="ema-filter"><option value="all">All</option><option value="above21">Above EMA21</option><option value="below21">At/below EMA21</option><option value="above50">Above EMA50</option><option value="below50">At/below EMA50</option></select></label>',
    );
    $("ema-filter").onchange = render;
    $("pool").onchange = render;
    function filtered(rows, p) {
      return filterRows(rows, {
        query: $(p + "-search").value,
        trend: $(p + "-trend").value,
        relative: $(p + "-relative").value,
      }).filter((r) =>
        p === "theme"
          ? $("level").value === "All" || r.level === $("level").value
          : (() => {
              let f = $("ema-filter").value;
              if (f === "all") return true;
              let n = f.endsWith("21") ? 21 : 50;
              if (!finite(r.price_close) || !finite(r["ema" + n])) return false;
              return f.startsWith("above")
                ? r.price_close > r["ema" + n]
                : r.price_close <= r["ema" + n];
            })(),
      );
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
      if (value === "Leading") return "broad";
      if (value === "Short-term strength only") return "narrow";
      if (value === "Medium-term strength only") return "internal";
      if (value === "Lagging") return "weak";
      return "unavailable";
    }
    function stateBadge(value) {
      return '<span class="state-pill state-' +
        themeStateType(value) +
        '">' + esc(value || "Unavailable") + "</span>";
    }
    function categoryBreadth(value, above, valid, coverage) {
      if (!finite(value)) return '<span class="muted">Unavailable</span>';
      return (
        '<span class="numeric">' +
        value.toFixed(1) +
        '% <small class="muted">' +
        (finite(above) ? above : "—") +
        "/" +
        (finite(valid) ? valid : "—") +
        '</small></span><br><small class="muted">' +
        (finite(coverage) ? coverage.toFixed(1) + "% data coverage" : "coverage unavailable") +
        "</small>"
      );
    }
    function categoryReturn(value, valid, eligible) {
      if (!finite(value)) return '<span class="muted">Unavailable</span>';
      const coverage = finite(valid) && eligible
        ? (100 * valid / eligible).toFixed(1) + "%"
        : "—";
      return (
        pct(value / 100) +
        '<br><small class="muted">' +
        (finite(valid) ? valid : "—") +
        "/" +
        (finite(eligible) ? eligible : "—") +
        " prices · " +
        coverage +
        " coverage</small>"
      );
    }
    function summaryCard(label, value, detail) {
      return '<article class="summary-card"><span>' +
        esc(label) +
        "</span><b>" +
        esc(value) +
        "</b><small>" +
        esc(detail) +
        "</small></article>";
    }
    function renderSectorPage() {
      const registry = (data.themes || []).filter((row) => row.level === "Sector");
      const sectorCatalog = data.classification_catalog?.sectors || [];
      const lookup = new Map(sectorCatalog.map((row) => [row.name, row]));
      const records = registry.map((row) =>
        Object.assign({}, row, {
          ticker: row.anchor,
          theme_name: row.name,
          constituent_count: lookup.get(row.name)?.company_count ?? null,
        }),
      );
      const ordered = ranked(records, state.sectorKey, state.sectorDir);
      const usableBreadth = registry
        .map((row) => row.etf_breadth21_pct)
        .filter(finite);
      const mean = usableBreadth.length
        ? (usableBreadth.reduce((a, b) => a + b, 0) / usableBreadth.length).toFixed(1) + "%"
        : "—";
      const leading = registry.filter((row) =>
        ["Leading", "Short-term strength only"].includes(row.theme_state),
      ).length;
      const coverage = registry
        .map((row) => row.breadth_coverage21_pct)
        .filter(finite);
      const meanCoverage = coverage.length
        ? (coverage.reduce((a, b) => a + b, 0) / coverage.length).toFixed(1) + "%"
        : "—";
      $("sector-summary").innerHTML =
        summaryCard("Sector ETFs", String(registry.length), "11 standard GICS sectors") +
        summaryCard("Above EMA21", mean, "Average across valid sector ETF breadth") +
        summaryCard("Price coverage", meanCoverage, "Average eligible holding coverage") +
        summaryCard("Current strength", String(leading), "Sector ETFs with CurrentStrength at or above 50");
      head("sector", [
        ["Rank"],
        ["Sector", "name"],
        ["ETF", "ticker"],
        ["S&P 500 companies", "constituent_count"],
        ["ThemeScore", "theme_score"],
        ["1M vs SPY (pp)", "excess21"],
        ["3M vs SPY (pp)", "excess63"],
        ["Above EMA21", "etf_breadth21_pct"],
        ["Above EMA50", "etf_breadth50_pct"],
        ["Holdings as of"],
        ["State"],
      ]);
      $("sector-body").innerHTML = ordered.map((row) =>
        '<tr><td>' +
        (row.display_rank || "—") +
        '</td><td class="category-name">' + esc(row.name) +
        '</td><td>' + (row.chart_url
          ? '<a class="etf-link" href="' + esc(row.chart_url) + '" target="_blank" rel="noopener noreferrer">' + esc(row.anchor) + " ↗</a>"
          : '<b>' + esc(row.anchor) + "</b>") +
        '</td><td>' + (finite(row.constituent_count) ? row.constituent_count : "—") +
        '</td><td>' + score(row, "theme_score") +
        '</td><td>' + pct(valueAt(row, "excess21"), true) +
        '</td><td>' + pct(valueAt(row, "excess63"), true) +
        '</td><td>' + categoryBreadth(row.etf_breadth21_pct, row.holdings_breadth?.["21"]?.above_count, row.holdings_breadth?.["21"]?.valid_count, row.breadth_coverage21_pct) +
        '</td><td>' + categoryBreadth(row.etf_breadth50_pct, row.holdings_breadth?.["50"]?.above_count, row.holdings_breadth?.["50"]?.valid_count, row.breadth_coverage50_pct) +
        '</td><td>' + esc(row.holdings_asof || "—") +
        '</td><td>' + stateBadge(row.theme_state) + "</td></tr>"
      ).join("") || '<tr><td colspan="11">Sector ETF data is unavailable.</td></tr>';
      $("sector-note").textContent =
        "ETF holdings are from each issuer’s official dated file. S&P 500 counts come from " +
        (data.classification_catalog?.source?.as_of || "the retrieved constituent source") +
        ". The holdings sample can include companies outside the S&P 500.";
    }
    function renderIndustryPage() {
      const catalog = data.classification_catalog || {};
      const industries = catalog.industries || [];
      const allRecords = ranked(industries, state.industryKey, state.industryDir);
      const query = $("industry-search").value.trim().toLowerCase();
      const records = allRecords.filter((row) => !query || row.name.toLowerCase().includes(query));
      const withReturn = industries.filter((row) => finite(row.median_return21_pct));
      const positive = withReturn.filter((row) => row.median_return21_pct > 0).length;
      const breadth = industries.map((row) => row.breadth21_pct).filter(finite);
      const cover = industries.map((row) => row.coverage21_pct).filter(finite);
      const avg = (values) => values.length
        ? (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1) + "%"
        : "—";
      $("industry-summary").innerHTML =
        summaryCard("GICS sub-industries", String(industries.length), "Represented in this S&P 500 snapshot") +
        summaryCard("Positive 1M median", positive + " / " + withReturn.length, "Valid industry medians above zero") +
        summaryCard("Above EMA21", avg(breadth), "Average valid industry participation") +
        summaryCard("Price coverage", avg(cover), "Average constituent history coverage");
      head("industry", [
        ["Rank"],
        ["Sector", "sector"],
        ["GICS sub-industry", "name"],
        ["Companies", "company_count"],
        ["Median 1M return", "median_return21_pct"],
        ["Above EMA21", "breadth21_pct"],
        ["Above EMA50", "breadth50_pct"],
        ["Median 3M return", "median_return63_pct"],
      ]);
      $("industry-body").innerHTML = records.map((row) =>
        '<tr><td>' + (row.display_rank || "—") +
        '</td><td>' + esc(row.sector || "—") +
        '</td><td class="category-name">' + esc(row.name) +
        '</td><td>' + row.company_count +
        '</td><td>' + categoryReturn(row.median_return21_pct, row.return21_valid_count, row.company_count) +
        '</td><td>' + categoryBreadth(row.breadth21_pct, row.above_ema21_count, row.valid_ema21_count, row.coverage21_pct) +
        '</td><td>' + categoryBreadth(row.breadth50_pct, row.above_ema50_count, row.valid_ema50_count, row.coverage50_pct) +
        '</td><td>' + categoryReturn(row.median_return63_pct, row.return63_valid_count, row.company_count) +
        "</td></tr>"
      ).join("") || '<tr><td colspan="8">Industry classification data is unavailable for this snapshot.</td></tr>';
      $("industry-count").textContent = records.length + " / " + industries.length + " industries shown";
      renderIndustryScatter(withReturn.filter((row) =>
        finite(row.median_return63_pct) && (!query || row.name.toLowerCase().includes(query)),
      ));
      $("industry-note").textContent =
        "Classification source observed " +
        (catalog.source?.as_of || "—") +
        " · prices through " +
        (data.session_date || "—") +
        " · " +
        (catalog.unclassified_count || 0) +
        " constituents lack a usable sector or sub-industry label. " +
        (catalog.method || "");
    }
    function renderIndustryScatter(points) {
      const width = 900, height = 390, left = 58, right = 24, top = 24, bottom = 42;
      if (!points.length) {
        $("industry-scatter").innerHTML = '<p class="chart-note">No categories have valid 1M and 3M constituent returns.</p>';
        return;
      }
      const xs = points.map((row) => row.median_return21_pct);
      const ys = points.map((row) => row.median_return63_pct);
      const extent = Math.max(1, ...xs.map(Math.abs), ...ys.map(Math.abs)) * 1.12;
      const x = (value) => left + ((value + extent) / (2 * extent)) * (width - left - right);
      const y = (value) => top + ((extent - value) / (2 * extent)) * (height - top - bottom);
      const zeroX = x(0), zeroY = y(0);
      $("industry-scatter").innerHTML =
        '<svg viewBox="0 0 ' + width + " " + height + '" role="img" aria-label="Scatter chart of GICS sub-industry median 1-month and 3-month constituent returns">' +
        '<line class="scatter-grid" x1="' + left + '" y1="' + top + '" x2="' + left + '" y2="' + (height - bottom) + '"/>' +
        '<line class="scatter-grid" x1="' + left + '" y1="' + (height - bottom) + '" x2="' + (width - right) + '" y2="' + (height - bottom) + '"/>' +
        '<line class="scatter-zero" x1="' + zeroX + '" y1="' + top + '" x2="' + zeroX + '" y2="' + (height - bottom) + '"/>' +
        '<line class="scatter-zero" x1="' + left + '" y1="' + zeroY + '" x2="' + (width - right) + '" y2="' + zeroY + '"/>' +
        '<text class="scatter-label" x="' + left + '" y="' + (height - 12) + '">1M median return: −' + extent.toFixed(1) + '%</text>' +
        '<text class="scatter-label" x="' + (width - 165) + '" y="' + (height - 12) + '">+' + extent.toFixed(1) + '%</text>' +
        '<text class="scatter-label" x="12" y="' + (top + 4) + '">3M +' + extent.toFixed(1) + '%</text>' +
        '<text class="scatter-label" x="12" y="' + (height - bottom) + '">−' + extent.toFixed(1) + '%</text>' +
        points.map((row) => {
          const q = row.median_return21_pct > 0 && row.median_return63_pct > 0
            ? "quadrant-strong"
            : row.median_return21_pct < 0 && row.median_return63_pct < 0
              ? "quadrant-weak"
              : row.median_return21_pct === 0 || row.median_return63_pct === 0
                ? "quadrant-neutral"
                : "quadrant-mixed";
          return '<circle class="industry-point ' + q + '" tabindex="0" cx="' +
            x(row.median_return21_pct).toFixed(2) + '" cy="' +
            y(row.median_return63_pct).toFixed(2) + '" r="5" aria-label="' +
            esc(row.name) + '"><title>' + esc(row.name + " · median 1M " +
            row.median_return21_pct.toFixed(2) + "% · median 3M " +
            row.median_return63_pct.toFixed(2) + "% · " + row.company_count +
            " S&P 500 companies · EMA21 coverage " +
            (finite(row.coverage21_pct) ? row.coverage21_pct.toFixed(1) + "%" : "unavailable")) +
            "</title></circle>";
        }).join("") +
        '</svg>';
    }
    function select(id) {
      state.theme = id;
      showPage("watchlist", true);
      render();
    }
    var visible = [];
    function render() {
      renderSectorPage();
      renderIndustryPage();
      ["theme", "stock"].forEach(
        (p) =>
          ($(p + "-direction").textContent =
            state[p + "Dir"] === "desc" ? "Descending ↓" : "Ascending ↑"),
      );
      var all = ranked(
          data.themes.filter((t) => t.level !== "Sector").map((t) =>
            Object.assign({}, t, { ticker: t.anchor, theme_name: t.name }),
          ),
          state.themeKey,
          state.themeDir,
        ),
        themes = filtered(all, "theme");
      $("theme-count").textContent =
        themes.length + " / " + all.length + " visible";
      $("theme-basis").textContent =
        "Rank: " +
        metrics[state.themeKey] +
        " · " +
        state.themeDir +
        " · full dated registry ranks retained across filters · " +
        data.session_date +
        " · " +
        (data.themes.find((t) => t.level !== "Sector")?.ranking_peer_count21 ?? all.length) +
        " valid 1M peers (10 required for scores)";
      head("theme", [
        ["Rank"],
        ["Level"],
        ["Theme"],
        ["ETF"],
        ["ThemeScore", "theme_score"],
        ["Current", "current_strength_score"],
        ["Medium", "medium_strength_score"],
        ["State"],
        ["1M vs SPY (pp)", "excess21"],
        ["3M vs SPY (pp)", "excess63"],
        ["Above EMA21", "etf_breadth21_pct"],
        ["Above EMA50", "etf_breadth50_pct"],
        ["ETF details"],
      ]);
      $("theme-body").innerHTML =
        themes
          .map(
            (t) =>
              '<tr data-theme="' +
              esc(t.id) +
              '" class="' +
              (t.id === state.theme ? "active" : "") +
              '"><td>' +
              (t.display_rank || "—") +
              "</td><td>" +
              esc(t.level || "Theme") +
              '</td><td><button class="theme-select">' +
              esc(t.name) +
              "</button></td><td>" +
              (t.chart_url ? '<a href="'+esc(t.chart_url)+'" target="_blank" rel="noopener noreferrer">'+esc(t.anchor)+' ↗</a>' : esc(t.anchor)) +
              "</td>" +
              ["theme_score", "current_strength_score", "medium_strength_score"]
                .map((k) => "<td>" + score(t, k) + "</td>")
                .join("") +
              "<td>" +
              stateBadge(t.theme_state) +
              "</td><td>" +
              pct(valueAt(t, "excess21"), true) +
              "</td><td>" +
              pct(valueAt(t, "excess63"), true) +
              "</td><td>" +
              breadth(t, 21) +
              "</td><td>" +
              breadth(t, 50) +
              '</td><td><details><summary>' +
              esc(t.stock_scope || "ETF-only") +
              " · " +
              (finite(t.theme_score) ? "Score valid" : "Score unavailable") +
              '</summary><div class="stock-details">' +
              esc(t.field_status?.theme_score?.reason || "Valid score") +
              "<br>ETF returns: 1W " +
              pct(valueAt(t, "return5")) +
              " · 1M " +
              pct(valueAt(t, "return21")) +
              " · 3M " +
              pct(valueAt(t, "return63")) +
              "<br>ETF price vs averages: EMA21 " +
              ema(t, 21) +
              " · EMA50 " +
              ema(t, 50) +
              "<br>1M percentile: " +
              esc(t.field_status?.percentile_excess21?.reason || "valid") +
              "<br>Anchor ETF holdings breadth, not whole-industry breadth. As of " +
              esc(t.holdings_asof || "unavailable") +
              "<br>" +
              esc(
                t.holdings_breadth?.["21"]?.reason || "Valid EMA21 coverage",
              ) +
              "<br>" +
              esc(
                t.holdings_breadth?.["50"]?.reason || "Valid EMA50 coverage",
              ) +
              "</div></details></td></tr>",
          )
          .join("") || '<tr><td colspan="13">No matching themes.</td></tr>';
      $("theme-body")
        .querySelectorAll("tr[data-theme]")
        .forEach((r) => (r.onclick = () => select(r.dataset.theme)));
      var t = data.themes.find((t) => t.id === state.theme);
      if (!t) return;
      $("active-name").textContent = "Watchlist · " + t.name + " / " + t.anchor;
      $("active-summary").innerHTML =
        "ETF 1M " +
        pct(valueAt(t, "return21")) +
        " · 3M " +
        pct(valueAt(t, "return63")) +
        " · " +
        trend(t) +
        " · ThemeScore " +
        score(t, "theme_score") +
        " · Current " +
        score(t, "current_strength_score") +
        " · Medium " +
        score(t, "medium_strength_score") +
        " · " +
        esc(t.theme_state || "Unavailable") +
        "<br>Anchor ETF holdings breadth: EMA21 " +
        breadth(t, 21) +
        " · EMA50 " +
        breadth(t, 50);
      var pool = $("pool").value,
        base =
          pool === "all"
            ? t.reviewed_universe
            : limitSelection(t.selected, Number(pool));
      base = base.map((r) =>
        Object.assign({}, r, { theme_id: t.id, theme_name: t.name }),
      );
      visible = filtered(ranked(base, state.stockKey, state.stockDir), "stock");
      $("stock-basis").textContent =
        visible.length +
        " / " +
        base.length +
        " visible · Rank: " +
        metrics[state.stockKey] +
        (state.stockKey.startsWith("excess")
          ? " versus " + t.anchor + " (pp)"
          : "") +
        " · within " +
        (pool === "all" ? "reviewed eligible subset" : "selected pool") +
        " only. Sorting does not change selection.";
      $("coverage").textContent =
        (base.length
          ? "Curated eligible stocks"
          : "ETF-only: no curated stock drilldown") +
        " · 15/20 is a browsing convention. Market-cap field timestamps remain unverified.";
      head("stock", [
        ["Rank"],
        ["Ticker / company"],
        ["Price", "price_close"],
        ["1W %", "return5"],
        ["1M %", "return21"],
        ["3M %", "return63"],
        ["1M vs theme (pp)", "excess21"],
        ["3M vs theme (pp)", "excess63"],
        ["EMA21"],
        ["EMA50"],
        ["Membership"],
        ["Trend"],
        ["ADV$30", "adv30_usd"],
        ["Chart"],
      ]);
      $("stock-body").innerHTML =
        visible
          .map((r) => {
            var exchange = String(r.exchange || "").toUpperCase(),
              prefix = exchange.startsWith("NASDAQ")
                ? "NASDAQ"
                : exchange.startsWith("NYSE")
                  ? "NYSE"
                  : null;
            var url = prefix
              ? "https://www.tradingview.com/chart/?symbol=" +
                encodeURIComponent(prefix + ":" + r.ticker)
              : null;
            r.chart_url = url;
            return (
              "<tr><td>" +
              (r.display_rank || "—") +
              "</td><td><b>" +
              esc(r.ticker) +
              '</b><span class="company" title="' +
              esc(r.company) +
              '">' +
              esc(r.company) +
              '</span><details><summary>Evidence & selection</summary><div class="stock-details">' +
              esc(r.membership_rationale || r.evidence_note || "") +
              "<br>" +
              esc(r.selection_reason || "Reviewed eligible subset") +
              "<br>" +
              esc(r.membership_source || r.evidence?.url || "") +
              "</div></details></td><td>" +
              money(r.price_close) +
              "</td>" +
              ["return5", "return21", "return63", "excess21", "excess63"]
                .map(
                  (k) =>
                    "<td>" +
                    pct(
                      valueAt(r, k),
                      k.startsWith("excess"),
                      (k.startsWith("excess") ? r.excess_returns : r.returns)?.[
                        k.replace(/\D/g, "")
                      ]?.reason,
                    ) +
                    "</td>",
                )
                .join("") +
              "<td>" +
              ema(r, 21) +
              "</td><td>" +
              ema(r, 50) +
              "</td><td>" +
              esc(r.membership_tag || "Unavailable") +
              "</td><td>" +
              trend(r) +
              "</td><td>" +
              money(r.adv30_usd, true) +
              "</td><td>" +
              (url
                ? '<a target="_blank" rel="noopener noreferrer" href="' +
                  esc(url) +
                  '">Open ↗</a>'
                : missing) +
              "</td></tr>"
            );
          })
          .join("") ||
        '<tr><td colspan="10">' +
          (base.length
            ? "No stocks match these filters."
            : "ETF-only. Valid ETF returns and holdings breadth remain independent of stock curation.") +
          "</td></tr>";
      var points = data.themes.filter(
          (t) =>
            finite(valueAt(t, "excess21")) && finite(valueAt(t, "excess63")),
        ),
        extent =
          Math.max(
            0.01,
            ...points.flatMap((t) => [
              Math.abs(valueAt(t, "excess21")),
              Math.abs(valueAt(t, "excess63")),
            ]),
          ) * 1.15;
      $("scatter").innerHTML =
        '<svg viewBox="0 0 600 260" role="img" aria-label="Theme excess-return scatter"><line x1="40" y1="130" x2="560" y2="130"/><line x1="300" y1="20" x2="300" y2="240"/><text x="43" y="16">1M negative / 3M positive</text><text x="350" y="16">Both positive</text><text x="43" y="255">Both negative</text><text x="350" y="255">1M positive / 3M negative</text>' +
        points
          .map(
            (t) =>
              '<circle tabindex="0" role="button" data-id="' +
              esc(t.id) +
              '" cx="' +
              (300 + (valueAt(t, "excess21") / extent) * 250) +
              '" cy="' +
              (130 - (valueAt(t, "excess63") / extent) * 105) +
              '" r="6" aria-label="' +
              esc(t.name) +
              '"><title>' +
              esc(t.name + " / " + t.anchor) +
              ": 1M " +
              (valueAt(t, "excess21") * 100).toFixed(2) +
              " pp; 3M " +
              (valueAt(t, "excess63") * 100).toFixed(2) +
              " pp</title></circle>",
          )
          .join("") +
        "</svg>";
      $("scatter")
        .querySelectorAll("circle")
        .forEach((c) => {
          c.onclick = () => select(c.dataset.id);
          c.onkeydown = (e) => {
            if (e.key === "Enter") select(c.dataset.id);
          };
        });
    }
    function download(name, text, type) {
      var url = URL.createObjectURL(new Blob([text], { type: type })),
        a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
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
    tradingViewExport: tradingViewExport,
    ranked: ranked,
  };
});
