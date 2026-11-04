/* Renders one page from data/*.json. No network beyond same-origin JSON. Chart.js is vendored. */
(function () {
  "use strict";
  var PAGE = document.body.getAttribute("data-page");
  var root = document.getElementById("app");
  var charts = [];

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function get(name) { return fetch("data/" + name + ".json").then(function (r) { if (!r.ok) throw new Error(name + ".json: HTTP " + r.status); return r.json(); }); }

  var theme = (function () {
    var t = null; try { t = localStorage.getItem("theme"); } catch (e) {}
    if (!t) t = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    return t;
  })();
  document.documentElement.setAttribute("data-theme", theme);

  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }

  var STATUS = { met: "Met", not_met: "Not met", not_computable: "Not computable on demo scope", diverges: "Diverges", match: "Match" };
  function pill(s) { var p = el("span", "pill " + s, STATUS[s] || s); return p; }
  function nf(n, d) { return Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }); }

  function cell(col, v, row) {
    var td = el("td");
    if (v === null || v === undefined || v === "") { td.className = "na"; td.textContent = col.fmt && col.fmt.indexOf("num") === 0 || col.fmt === "inr" ? "n/a" : "n/a"; return td; }
    switch (col.fmt) {
      case "int": td.className = "num"; td.textContent = nf(v, 0); break;
      case "num0": td.className = "num"; td.textContent = nf(v, 0); break;
      case "num1": td.className = "num"; td.textContent = nf(v, 1); break;
      case "num2": td.className = "num"; td.textContent = nf(v, 2); break;
      case "inr": td.className = "num"; td.textContent = nf(v, 2); break;
      case "bool": td.textContent = v ? "Yes" : "No"; break;
      case "status": td.appendChild(pill(v)); break;
      case "link": var a = el("a", null, "Open"); a.href = v + ".html"; td.appendChild(a); break;
      default: td.textContent = String(v);
    }
    return td;
  }

  function table(t) {
    var card = el("section", "card"); card.appendChild(el("h3", null, t.title));
    var wrap = el("div", "tablewrap"); wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", t.title);
    var tb = el("table"), thead = el("thead"), hr = el("tr");
    t.columns.forEach(function (c) { var th = el("th", c.fmt && /^(int|num|inr)/.test(c.fmt) ? "num" : null, c.label); th.scope = "col"; hr.appendChild(th); });
    thead.appendChild(hr); tb.appendChild(thead);
    var body = el("tbody");
    t.rows.forEach(function (r) { var tr = el("tr"); t.columns.forEach(function (c) { tr.appendChild(cell(c, r[c.key], r)); }); body.appendChild(tr); });
    tb.appendChild(body); wrap.appendChild(tb); card.appendChild(wrap);
    card.appendChild(el("p", "chartnote", t.rows.length + " rows"));
    return card;
  }

  function tile(t) {
    var d = el("article", "tile" + (t.status ? " k-" + t.status : ""));
    d.appendChild(el("div", "label", t.label));
    d.appendChild(el("div", "value", t.value));
    if (t.status) { var s = el("div"); s.appendChild(pill(t.status)); d.appendChild(s); }
    if (t.extra && t.extra.target) d.appendChild(row("Target", t.extra.target));
    d.appendChild(row("Period", t.period)); d.appendChild(row("Baseline", t.baseline)); d.appendChild(row("Refreshed", t.refreshed));
    var det = el("details"); det.appendChild(el("summary", null, "Definition and source"));
    det.appendChild(el("div", null, t.definition)); det.appendChild(el("div", null, "Source: " + t.source)); d.appendChild(det);
    return d;
  }
  function row(k, v) { var r = el("div", "row"); r.appendChild(el("b", null, k + ": ")); r.appendChild(document.createTextNode(v)); return r; }

  function baseOpts() {
    var text = css("--text"), muted = css("--muted"), line = css("--line");
    return { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { color: text, boxWidth: 14 } }, tooltip: { enabled: true } },
      scales: { x: { ticks: { color: muted, maxRotation: 60, autoSkip: true, maxTicksLimit: 14 }, grid: { color: line } },
                y: { ticks: { color: muted, callback: function (v) { return Math.abs(v) >= 1e6 ? (v / 1e6) + "M" : Math.abs(v) >= 1e4 ? (v / 1e3) + "k" : v; } }, grid: { color: line } } } };
  }
  var COL = function () { return [css("--c1"), css("--c2"), css("--c3"), css("--c4")]; };

  function chart(c) {
    var card = el("section", "card"); card.appendChild(el("h3", null, c.title));
    var box = el("div", "chartbox"), cv = el("canvas"); cv.setAttribute("role", "img"); cv.setAttribute("aria-label", c.title);
    box.appendChild(cv); card.appendChild(box);
    if (c.note) card.appendChild(el("p", "chartnote", c.note));
    var o = baseOpts(), col = COL(), cfg;
    if (c.type === "forecast") {
      function ds(label, data, color, extra) { return Object.assign({ label: label, data: data, borderColor: color, backgroundColor: color, pointRadius: 3, borderWidth: 2, spanGaps: false, tension: 0 }, extra || {}); }
      var datasets = [
        ds("History (actual net issues)", c.history, col[0]),
        ds("Holdout: actual", c.holdout_actual, col[0], { borderDash: [], pointStyle: "rectRot", pointRadius: 5 }),
        ds("Holdout: model forecast (not seen in training)", c.holdout_predicted, col[1], { borderDash: [6, 4] }),
        ds("Holdout: engine upper bound", c.holdout_upper, col[1], { borderWidth: 1, pointRadius: 0, borderDash: [2, 3], fill: "+1", backgroundColor: css("--band") }),
        ds("Holdout: engine lower bound", c.holdout_lower, col[1], { borderWidth: 1, pointRadius: 0, borderDash: [2, 3] }),
        ds("Forward forecast (ContextFlow predict-batch)", c.forward, col[2], { borderDash: [4, 3], pointStyle: "triangle", pointRadius: 5 })
      ];
      cfg = { type: "line", data: { labels: c.labels, datasets: datasets }, options: o };
    } else if (c.type === "line") {
      cfg = { type: "line", data: { labels: c.labels, datasets: c.series.map(function (s, i) { return { label: s.name, data: s.data, borderColor: col[i], backgroundColor: col[i], pointRadius: 2, borderWidth: 2, tension: 0 }; }) }, options: o };
    } else {
      var stacked = c.type === "stackedbar"; o.scales.x.stacked = stacked; o.scales.y.stacked = stacked;
      cfg = { type: "bar", data: { labels: c.labels, datasets: c.series.map(function (s, i) { return { label: s.name, data: s.data, backgroundColor: col[i], borderColor: col[i] }; }) }, options: o };
    }
    charts.push({ canvas: cv, cfg: cfg, chart: null });
    return card;
  }
  function drawCharts() {
    charts.forEach(function (c) { if (c.chart) c.chart.destroy(); c.cfg.options = baseOpts(); if (c.cfg.options && c.cfg.type === "bar" && c.cfg.data.datasets.length > 0) { var st = c.cfg.data.datasets.length > 1 && c.canvas.getAttribute("aria-label").indexOf("by PR type") > -1; c.cfg.options.scales.x.stacked = st; c.cfg.options.scales.y.stacked = st; }
      var cols = COL(); c.cfg.data.datasets.forEach(function (d, i) { if (c.cfg.type === "bar") { d.backgroundColor = cols[i]; d.borderColor = cols[i]; } });
      c.chart = new Chart(c.canvas, c.cfg);
      var pts = 0; c.cfg.data.datasets.forEach(function (d) { d.data.forEach(function (v) { if (v !== null && v !== undefined) pts++; }); });
      var info = c.canvas.parentNode.parentNode.querySelector(".plotted");
      if (!info) { info = el("p", "chartnote plotted"); c.canvas.parentNode.parentNode.appendChild(info); }
      info.textContent = "Plotted: " + c.cfg.data.datasets.length + " series, " + pts + " points, " + c.cfg.data.labels.length + " months.";
    });
  }

  function notes(list) {
    if (!list || !list.length) return null;
    var card = el("section", "card"); card.appendChild(el("h3", null, "Notes")); var ul = el("ul", "notes");
    list.forEach(function (n) { ul.appendChild(el("li", null, n)); }); card.appendChild(ul); return card;
  }

  function render(meta, sec) {
    root.textContent = "";
    root.appendChild(el("h2", null, sec.title)); root.appendChild(el("p", "intro", sec.intro));
    if (sec.tiles && sec.tiles.length) { var g = el("div", "grid"); sec.tiles.forEach(function (t) { g.appendChild(tile(t)); }); root.appendChild(g); }
    (sec.charts || []).forEach(function (c) { root.appendChild(chart(c)); });
    (sec.tables || []).forEach(function (t) { root.appendChild(table(t)); });
    var n = notes(sec.notes); if (n) root.appendChild(n);
  }

  function renderOverview(meta, kpis, sec1) {
    root.textContent = "";
    root.appendChild(el("h2", null, "KPI overview")); root.appendChild(el("p", "intro", sec1.intro));
    var g = el("div", "grid");
    kpis.forEach(function (k) {
      var d = el("article", "tile k-" + k.status);
      d.appendChild(el("div", "label", "KPI " + k.kpi + ": " + k.name));
      d.appendChild(el("div", "value", k.display));
      var s = el("div"); s.appendChild(pill(k.status)); d.appendChild(s);
      d.appendChild(row("Target", k.target)); d.appendChild(row("Period", k.period)); d.appendChild(row("Baseline", k.baseline)); d.appendChild(row("Refreshed", meta.refreshed));
      var det = el("details"); det.appendChild(el("summary", null, "Definition, detail and drill-down"));
      det.appendChild(el("div", null, "Definition: " + k.definition)); det.appendChild(el("div", null, k.detail));
      if (k.curated) det.appendChild(el("div", null, k.curated.label + ": " + k.curated.display));
      var a = el("a", null, "Open drill-down"); a.href = k.drill + ".html"; det.appendChild(a); d.appendChild(det); g.appendChild(d);
    });
    root.appendChild(g);
    var cnt = meta.kpi_counts, c = el("section", "card"); c.appendChild(el("h3", null, "Engine and model"));
    var e = meta.engine; var ul = el("ul", "notes");
    ["ContextFlow on-prem engine, experiment " + e.experiment_id + ". Best model as returned: " + e.best_model + ", " + e.primary_metric + " " + e.wql + ".",
     "KPI status: " + cnt.met + " met, " + cnt.not_met + " not met, " + cnt.not_computable + " not computable on demo scope.", meta.scope_note].forEach(function (t) { ul.appendChild(el("li", null, t)); });
    c.appendChild(ul); root.appendChild(c);
  }

  function chrome(meta) {
    var b = document.getElementById("banner"); b.textContent = meta.banner;
    var sub = document.getElementById("sub"); sub.textContent = "As-of " + meta.as_of + ", INR, " + meta.plant + ". " + meta.refreshed + ".";
    var nav = document.getElementById("menu"); nav.textContent = "";
    var items = [{ id: "index", nav: "KPI overview", href: "index.html" }].concat(meta.sections.slice(1).map(function (s) { return { id: s.id, nav: s.nav, href: s.id + ".html" }; }))
      .concat(meta.extra.map(function (s) { return { id: s.id, nav: s.nav, href: s.id + ".html" }; }));
    items.forEach(function (i) { var a = el("a", null, i.nav); a.href = i.href; if (i.id === PAGE) a.setAttribute("aria-current", "page"); nav.appendChild(a); });
    var btn = document.getElementById("theme");
    btn.textContent = theme === "dark" ? "Light theme" : "Dark theme";
    btn.addEventListener("click", function () {
      theme = theme === "dark" ? "light" : "dark"; try { localStorage.setItem("theme", theme); } catch (e) {}
      document.documentElement.setAttribute("data-theme", theme); btn.textContent = theme === "dark" ? "Light theme" : "Dark theme"; drawCharts();
    });
    document.getElementById("foot").textContent = meta.banner + " Synthetic POC data, read-only SAP HANA (VEDANTA_POC). Every figure on this page is read from data/" + (PAGE === "index" ? "kpis.json" : PAGE + ".json") + ".";
  }

  get("meta").then(function (meta) {
    chrome(meta);
    document.title = (PAGE === "index" ? "KPI overview" : (meta.sections.concat(meta.extra).filter(function (s) { return s.id === PAGE; })[0] || {}).nav) + " | HZL_DEMO inventory";
    if (PAGE === "index") return Promise.all([get("kpis"), get("sec01_kpi_scorecard")]).then(function (r) { renderOverview(meta, r[0], r[1]); });
    return get(PAGE).then(function (sec) { render(meta, sec); });
  }).then(drawCharts).catch(function (e) { root.textContent = ""; root.appendChild(el("div", "err", "This page could not load its data: " + e.message)); console.error(e); });
})();
