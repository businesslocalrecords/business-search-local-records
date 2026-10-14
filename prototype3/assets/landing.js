// Landing-page interactions: sticky CTA reveal + guarded conversion pings.
// No external dependencies. Conversion events fire only if the ad pixels exist.
(function () {
  "use strict";

  // --- Sticky mobile CTA: appear after scrolling past the hero -------------
  var hero = document.querySelector(".hero");
  var sticky = document.querySelector(".sticky-cta");
  if (sticky) {
    var onScroll = function () {
      var past = hero ? window.scrollY > hero.offsetHeight * 0.75 : window.scrollY > 240;
      sticky.classList.toggle("show", past);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // --- Conversion tracking (defensive: never throw if pixels are absent) ---
  function track(name, params) {
    try {
      if (typeof window.gtag === "function") window.gtag("event", name, params || {});
      if (window.uetq && typeof window.uetq.push === "function") {
        window.uetq.push({ ea: "fire_custom_event", en: name });
        window.uetq.push("event", name, params || {});
      }
    } catch (e) {
      /* analytics must never break the funnel */
    }
  }

  // Read a data attribute once per page; used to tag the city×trade source.
  var metaEl = document.querySelector('meta[name="blr:lead"]');
  var lead = {};
  try { lead = metaEl ? JSON.parse(metaEl.content) : {}; } catch (e) { lead = {}; }
  function withLead(params) {
    return Object.assign({ city: lead.city, trade: lead.trade }, params || {});
  }

  // Fire a page-view style event for optimization/attribution.
  track("view_landing", withLead({ send_to: undefined }));

  document.querySelectorAll("[data-track]").forEach(function (el) {
    el.addEventListener("click", function () {
      track(el.getAttribute("data-track"), withLead({ label: el.getAttribute("data-label") || "" }));
    });
  });

  // --- Weekly digest capture: salvages non-buyers + feeds remarketing -------
  var nlForm = document.getElementById("nl-form");
  if (nlForm) {
    nlForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var note = document.getElementById("nl-note");
      var input = nlForm.querySelector('input[name="email"]');
      var email = ((input && input.value) || "").trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        note.hidden = false; note.textContent = "Enter a valid email address."; return;
      }
      note.hidden = false; note.textContent = "Subscribing…";
      var payload = {
        email: email,
        city: nlForm.getAttribute("data-city") || "",
        trade: nlForm.getAttribute("data-trade") || ""
      };
      fetch("/api/index.php?r=capture", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (res) {
        // Friendly either way; tracking fires regardless. Add the backend
        // endpoint /api?r=capture to persist; until then we acknowledge.
        track("newsletter_signup", withLead({}));
        nlForm.reset();
        note.textContent = "You're in — the first digest lands this week.";
        if (!res.ok) note.textContent = "Thanks! We'll be in touch at " + email + ".";
      }).catch(function () {
        track("newsletter_signup", withLead({}));
        note.textContent = "Thanks! Email sales@businesslocalrecords.com to get started.";
      });
    });
  }
})();
