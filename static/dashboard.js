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
      var aMissing =
        av === null || av === undefined || !Number.isFinite(Number(av));
      var bMissing =
        bv === null || bv === undefined || !Number.isFinite(Number(bv));
      if (aMissing !== bMissing) return aMissing ? 1 : -1;
      if (!aMissing && Number(av) !== Number(bv))
        return sign * (Number(av) - Number(bv));
      return String(a.ticker || a.id || "").localeCompare(
        String(b.ticker || b.id || ""),
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
    $("date").textContent = data.session_date || "Unavailable";
    $("generated").textContent =
      "Collected " +
      (data.generated_at || "unknown") +
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
    $("status").textContent =
      "Dated snapshot · provisional reviewed stock subset; membership screening is incomplete.";
    $("cards").innerHTML = data.context
      .map(
        (r) =>
          '<article class="card"><div class="card-top"><b>' +
          esc(r.ticker) +
          "</b>" +
          trend(r) +
          '</div><div class="card-content"><div><span class="price">' +
          money(r.price_close) +
          '</span><span title="Latest regular-session change; split-adjusted closing prices">' +
          pct(r.daily_change) +
          '</span><div class="returns">' +
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
          spark(r.history) +
          '</div><small title="(Split-adjusted close / EMA − 1) × 100; same close series for price and EMA">Distance to EMA21 ' +
          pct(r.ema21_distance) +
          " · EMA50 " +
          pct(r.ema50_distance) +
          "</small><br><small>EMA21 five-session slope: " +
          (finite(r.ema21_slope_5)
            ? (r.ema21_slope_5 > 0 ? "+" : "") +
              r.ema21_slope_5.toFixed(2) +
              " USD"
            : "—") +
          "</small></article>",
      )
      .join("");
    var metrics = {
      return5: "1W return",
      return21: "1M return",
      return63: "3M return",
      excess21: "1M excess",
      excess63: "3M excess",
      price_close: "Price",
      adv30_usd: "ADV$30",
    };
    var state = {
      theme: data.themes[0]?.id,
      themeKey: "excess21",
      themeDir: "desc",
      stockKey: "excess21",
      stockDir: "desc",
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
              ? k !== "excess63"
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
          ["All", "Outperforming", "Underperforming"].map((v) => [
            v,
            v,
          ]),
        ) +
        "</select></label>" +
        (stock
          ? '<label>Pool <select id="pool"><option value="15">Selected 15</option><option value="20">Selected 20</option><option value="all">All reviewed eligible (incomplete)</option></select></label>'
          : "")
      );
    }
    $("theme-controls").innerHTML = controls("theme", false);
    $("stock-controls").innerHTML = controls("stock", true);
    ["theme", "stock"].forEach(function (p) {
      $(p + "-sort").value = "excess21";
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
    $("pool").onchange = render;
    function filtered(rows, p) {
      return filterRows(rows, {
        query: $(p + "-search").value,
        trend: $(p + "-trend").value,
        relative: $(p + "-relative").value,
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
              $(p + "-sort").value = key;
              render();
            }),
        );
    }
    function select(id) {
      state.theme = id;
      render();
    }
    var visible = [];
    function render() {
      ["theme", "stock"].forEach(
        (p) =>
          ($(p + "-direction").textContent =
            state[p + "Dir"] === "desc" ? "Descending ↓" : "Ascending ↑"),
      );
      var all = ranked(
          data.themes.map((t) =>
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
        (state.themeKey.startsWith("excess") ? " versus SPY (pp)" : " (%)") +
        " · " +
        state.themeDir +
        " · ranks retained across filters";
      head("theme", [
        ["Rank"],
        ["Theme"],
        ["ETF"],
        ["1W %", "return5"],
        ["1M %", "return21"],
        ["3M %", "return63"],
        ["1M vs SPY (pp)", "excess21"],
        ["3M vs SPY (pp)", "excess63"],
        ["Trend"],
        ["64-session close"],
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
              '</td><td><button class="theme-select" data-id="' +
              esc(t.id) +
              '">' +
              esc(t.name) +
              "</button></td><td>" +
              esc(t.anchor) +
              "</td>" +
              ["return5", "return21", "return63", "excess21", "excess63"]
                .map(
                  (k) =>
                    "<td>" +
                    pct(
                      valueAt(t, k),
                      k.startsWith("excess"),
                      (k.startsWith("excess") ? t.excess_returns : t.returns)?.[
                        k.replace(/\D/g, "")
                      ]?.reason,
                    ) +
                    "</td>",
                )
                .join("") +
              "<td>" +
              trend(t) +
              "</td><td>" +
              spark(t.history) +
              "</td></tr>",
          )
          .join("") ||
        '<tr><td colspan="10">No themes match these filters.</td></tr>';
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
        trend(t);
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
        t.pending_count +
        " holdings pending review · " +
        t.eligible_reviewed_count +
        " provisional eligible. " +
        (t.review_reason || "") +
        " Market-cap timestamps are unverified. 15/20 is a browsing convention.";
      head("stock", [
        ["Rank"],
        ["Ticker / company"],
        ["Price", "price_close"],
        ["1W %", "return5"],
        ["1M %", "return21"],
        ["3M %", "return63"],
        ["1M vs theme (pp)", "excess21"],
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
              esc(r.evidence_note || "") +
              "<br>" +
              esc(r.selection_reason || "Reviewed eligible subset") +
              "<br>" +
              esc(r.evidence?.url || "") +
              "</div></details></td><td>" +
              money(r.price_close) +
              "</td>" +
              ["return5", "return21", "return63", "excess21"]
                .map(
                  (k) =>
                    "<td>" +
                    pct(
                      valueAt(r, k),
                      k === "excess21",
                      (k.startsWith("excess") ? r.excess_returns : r.returns)?.[
                        k.replace(/\D/g, "")
                      ]?.reason,
                    ) +
                    "</td>",
                )
                .join("") +
              "<td>" +
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
            : "No reviewed stocks passed selection. " +
              esc(t.review_reason || "See diagnostics for pending evidence.")) +
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
