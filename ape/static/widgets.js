/* APE report widgets — progressive enhancement.
 *
 * Every chart is already on the page as an inline SVG before this file
 * runs. Nothing here is required for the report to be readable or complete;
 * it upgrades what is there. If ECharts fails to load, if scripting is off,
 * or if any single option is malformed, the SVG simply stays and the report
 * is exactly what it was.
 *
 * That ordering is deliberate. A client's quarterly report is a record, and
 * a record that renders only when a 1MB script succeeds is not a record.
 *
 * FACTS ARE NEVER TOUCHED. Tooltips restate figures already bound to the
 * frozen snapshot. The count-up animation restores the server-rendered
 * string exactly on its final frame — it animates toward the number the
 * server wrote and then defers to it, so no rounding introduced here can
 * ever survive into what the client reads.
 */
(function () {
  "use strict";

  var STATIC = /[?&]static=1/.test(location.search) ||
               window.APE_STATIC === true;
  var REDUCED = window.matchMedia &&
                window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var STILL = STATIC || REDUCED;

  var charts = [];

  // -- number formatting ----------------------------------------------------
  // The option travels as JSON and cannot carry callbacks, so the server
  // sends a `_ape` hint and the formatter is installed here.
  function makeFormatter(meta) {
    var unit = (meta && meta.unit) || "";
    var dp = (meta && typeof meta.dp === "number") ? meta.dp : 2;
    return function (v) {
      if (v === null || v === undefined || v === "-" || isNaN(v)) return "–";
      var n = Number(v);
      var body = n.toLocaleString(undefined, {
        minimumFractionDigits: dp, maximumFractionDigits: dp
      });
      if (unit === "%") return body + "%";
      if (unit && /^[£$€]$/.test(unit)) return unit + body;
      return unit ? body + " " + unit : body;
    };
  }

  function installFormatters(opt) {
    var meta = opt._ape;
    delete opt._ape;
    var fmt = makeFormatter(meta);

    if (opt.tooltip && !opt.tooltip.valueFormatter) {
      opt.tooltip.valueFormatter = fmt;
    }
    // Axis labels get a compact form: full precision on every gridline is
    // noise, and the exact value is one hover away.
    var compact = function (v) {
      var n = Number(v);
      if (!isFinite(n)) return v;
      var a = Math.abs(n);
      if (a >= 1e9) return (n / 1e9).toFixed(1) + "bn";
      if (a >= 1e6) return (n / 1e6).toFixed(1) + "m";
      if (a >= 1e4) return (n / 1e3).toFixed(0) + "k";
      var s = (a >= 100 || Number.isInteger(n)) ? n.toFixed(0) : n.toFixed(1);
      return (meta && meta.unit === "%") ? s + "%" : s;
    };
    ["xAxis", "yAxis"].forEach(function (k) {
      var ax = opt[k];
      if (!ax) return;
      (Array.isArray(ax) ? ax : [ax]).forEach(function (a) {
        if (a && a.type === "value") {
          a.axisLabel = a.axisLabel || {};
          if (!a.axisLabel.formatter) a.axisLabel.formatter = compact;
        }
      });
    });
    return opt;
  }

  // -- chart init -----------------------------------------------------------
  function initChart(box) {
    var raw = box.getAttribute("data-opt");
    if (!raw || typeof echarts === "undefined") return;

    var opt;
    try { opt = JSON.parse(raw); } catch (e) { return; }
    try { opt = installFormatters(opt); } catch (e) { return; }

    if (STILL) {
      opt.animation = false;
      if (opt.series) {
        (Array.isArray(opt.series) ? opt.series : [opt.series])
          .forEach(function (s) { s.animation = false; });
      }
    }

    var host = box.querySelector(".ecw-live");
    if (!host) return;

    var inst;
    try {
      // SVG rather than canvas: these charts are small, and a report is
      // printed and zoomed more often than it is scrolled.
      inst = echarts.init(host, null, { renderer: "svg" });
      inst.setOption(opt);
    } catch (e) {
      return;                       // the fallback SVG stays visible
    }

    // Only once the live chart has actually drawn does the static one go.
    box.classList.add("is-live");
    charts.push(inst);

    // The viewer's chat pane is drag-resizable, so the document column
    // changes width with no window resize behind it. Watching the box
    // itself is the only thing that catches that.
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () {
        try { inst.resize(); } catch (e) {}
      });
      ro.observe(box);
    }

    if (box.getAttribute("data-kind") === "donut") centreReadout(inst, box, opt);
  }

  // A donut's middle is empty space. Put the reading for whatever the
  // pointer is on into it, and the share of the whole alongside.
  function centreReadout(inst, box, opt) {
    var el = document.createElement("div");
    el.className = "ecw-centre";
    box.appendChild(el);

    var data = ((opt.series || [])[0] || {}).data || [];
    var total = data.reduce(function (a, d) { return a + (Number(d.value) || 0); }, 0);

    function show(d) {
      if (!d) { el.innerHTML = ""; el.classList.remove("on"); return; }
      var pct = total ? (Number(d.value) / total * 100) : 0;
      el.innerHTML = '<b>' + pct.toFixed(1) + '%</b><span></span>';
      el.querySelector("span").textContent = d.name || "";
      el.classList.add("on");
    }
    inst.on("mouseover", function (p) { if (p.data) show(p.data); });
    inst.on("mouseout", function () { show(null); });
  }

  // -- tables ---------------------------------------------------------------
  // Sortable columns, because the one question a holdings table always
  // provokes is "which is the biggest".
  function parseCell(td) {
    var t = (td.textContent || "").trim();
    var n = parseFloat(t.replace(/[^0-9.\-+]/g, ""));
    return isNaN(n) ? t.toLowerCase() : n;
  }

  function enhanceTable(tbl) {
    var head = tbl.querySelector("tr");
    if (!head) return;
    var body = Array.prototype.slice.call(tbl.querySelectorAll("tr")).slice(1);
    // A totals row is a summary of the rows above it, so it must not be
    // sorted in among them.
    var totals = body.filter(function (r) { return r.classList.contains("tot"); });
    var rows = body.filter(function (r) { return !r.classList.contains("tot"); });
    if (rows.length < 3) return;

    var ths = head.querySelectorAll("th");
    if (!ths.length) return;
    tbl.classList.add("sortable");

    Array.prototype.forEach.call(ths, function (th, i) {
      // A column with no heading is a visual one — an in-cell bar, say.
      // It has nothing to sort by, and offering the control anyway means
      // a click that appears to do nothing.
      if (!(th.textContent || "").trim()) {
        th.classList.add("nosort");
        return;
      }
      th.tabIndex = 0;
      th.setAttribute("role", "button");
      var dir = 0;
      function sort() {
        dir = dir === 1 ? -1 : 1;
        Array.prototype.forEach.call(ths, function (o) {
          o.removeAttribute("data-sort");
        });
        th.setAttribute("data-sort", dir === 1 ? "asc" : "desc");
        rows.sort(function (a, b) {
          var x = parseCell(a.cells[i]), y = parseCell(b.cells[i]);
          if (x === y) return 0;
          return (x > y ? 1 : -1) * dir;
        });
        var parent = rows[0].parentNode;
        rows.forEach(function (r) { parent.appendChild(r); });
        totals.forEach(function (r) { parent.appendChild(r); });
      }
      th.addEventListener("click", sort);
      th.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); }
      });
    });
  }

  // -- KPI count-up ---------------------------------------------------------
  // The server-rendered string is authoritative. We animate toward it and
  // then write it back verbatim, so the figure a client reads is always the
  // one the grounding validator saw.
  function countUp(el) {
    var final = el.textContent;
    var m = final.match(/^([^0-9\-+]*)([-+]?[\d,]*\.?\d+)(.*)$/);
    if (!m) return;
    var pre = m[1], suf = m[3];
    var target = parseFloat(m[2].replace(/,/g, ""));
    if (!isFinite(target)) return;
    var dp = (m[2].split(".")[1] || "").length;
    var grouped = m[2].indexOf(",") >= 0;
    var signed = /^[-+]/.test(m[2]);

    var t0 = null, dur = 620;
    function frame(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      if (p >= 1) { el.textContent = final; return; }
      var v = target * eased;
      var body = Math.abs(v).toLocaleString(undefined, {
        minimumFractionDigits: dp, maximumFractionDigits: dp,
        useGrouping: grouped
      });
      var sign = v < 0 ? "-" : (signed ? "+" : "");
      el.textContent = pre + sign + body + suf;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // -- reveal ---------------------------------------------------------------
  // Sections fade in as they are scrolled to. Purely presentational, and
  // skipped entirely when the reader has asked for less motion or when we
  // are rendering for print.
  function reveal(root) {
    if (STILL || !("IntersectionObserver" in window)) return;
    var secs = root.querySelectorAll("section[data-block-id]");
    if (!secs.length) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add("shown");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -40px 0px", threshold: 0.04 });
    Array.prototype.forEach.call(secs, function (s) {
      s.classList.add("reveal");
      io.observe(s);
    });
  }

  // -- entry ----------------------------------------------------------------
  function enhance(root) {
    root = root || document;
    Array.prototype.forEach.call(root.querySelectorAll(".ecw:not(.is-done)"),
      function (b) { b.classList.add("is-done"); initChart(b); });
    Array.prototype.forEach.call(root.querySelectorAll("table:not(.is-done)"),
      function (t) { t.classList.add("is-done"); enhanceTable(t); });
    if (!STILL) {
      Array.prototype.forEach.call(root.querySelectorAll(".kpi b:not(.is-done)"),
        function (b) { b.classList.add("is-done"); countUp(b); });
    }
    reveal(root);
    // The PDF pass waits on this rather than on a fixed timeout, so a slow
    // render produces a slow PDF instead of a half-drawn one.
    window.__apeWidgetsReady = true;
  }

  var resizeTimer;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      charts.forEach(function (c) { try { c.resize(); } catch (e) {} });
    }, 120);
  });

  // Charts must be laid out before print, or they print at their pre-resize
  // size. Both hooks fire in headless Chromium's PDF path too.
  window.addEventListener("beforeprint", function () {
    charts.forEach(function (c) { try { c.resize(); } catch (e) {} });
  });

  window.apeEnhanceWidgets = enhance;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { enhance(); });
  } else {
    enhance();
  }
})();
