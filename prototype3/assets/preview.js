// Live interactive preview on the landing pages.
// Rows are server-rendered (matches the board); this adds sort + quick filters
// and re-applies the "first N free, rest gated" blur after each change.
// Unlock/sign-in always navigate the top-level page (never in-frame).
(function () {
  "use strict";

  var FREE_ROWS = 6;

  document.querySelectorAll(".live-preview").forEach(function (root) {
    var tbody = root.querySelector("#pv-body");
    if (!tbody) return;
    var rows = Array.prototype.slice.call(tbody.querySelectorAll(".pv-row"));
    var gate = root.querySelector(".pv-gate");
    if (!rows.length) { if (gate) gate.hidden = true; return; }

    // Cache typed sort keys once.
    var model = rows.map(function (tr) {
      var raw = tr.getAttribute("data-value");
      var v = raw === "" || raw === null ? null : parseFloat(raw);
      return { el: tr, value: isNaN(v) ? null : v, issued: tr.getAttribute("data-issued") || "" };
    });

    var state = { filter: "all", sort: "value" };

    function passes(row) {
      if (state.filter === "100k") return row.value !== null && row.value >= 100000;
      if (state.filter === "10-50k") return row.value !== null && row.value >= 10000 && row.value < 50000;
      return true;
    }

    function sortRows(a, b) {
      if (state.sort === "issued") {
        return a.issued < b.issued ? 1 : (a.issued > b.issued ? -1 : 0);
      }
      // value desc, nulls last
      var an = a.value === null, bn = b.value === null;
      if (an && bn) return 0;
      if (an) return 1;
      if (bn) return -1;
      return b.value - a.value;
    }

    function render() {
      var shown = model.filter(passes).sort(sortRows);
      // Re-order DOM to match, then gate everything past the first FREE_ROWS.
      shown.forEach(function (row, i) {
        tbody.appendChild(row.el); // append reorders existing nodes
        row.el.classList.toggle("row-gated", i >= FREE_ROWS);
        row.el.setAttribute("aria-hidden", i >= FREE_ROWS ? "true" : "false");
      });
      if (gate) gate.hidden = shown.length <= FREE_ROWS;
      // Keep a footer counter in sync if present.
      var counter = root.querySelector("[data-pv-shown]");
      if (counter) counter.textContent = String(Math.min(shown.length, FREE_ROWS));
    }

    root.querySelectorAll(".pv-chip").forEach(function (btn) {
      btn.addEventListener("click", function () {
        root.querySelectorAll(".pv-chip").forEach(function (b) { b.classList.remove("on"); });
        btn.classList.add("on");
        state.filter = btn.getAttribute("data-filter");
        render();
      });
    });
    root.querySelectorAll(".pv-sort").forEach(function (btn) {
      btn.addEventListener("click", function () {
        root.querySelectorAll(".pv-sort").forEach(function (b) { b.classList.remove("on"); });
        btn.classList.add("on");
        state.sort = btn.getAttribute("data-sort");
        render();
      });
    });

    // Clicking a gated row nudges toward unlock.
    tbody.addEventListener("click", function (e) {
      var gated = e.target.closest(".pv-row.row-gated");
      if (gated) {
        var link = root.querySelector(".pv-gate-actions .btn-primary");
        if (link) link.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });

    render();
  });
})();
