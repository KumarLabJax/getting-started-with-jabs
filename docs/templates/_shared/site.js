/* ==========================================================================
   Getting Started with JABS - shared site behaviors
   ==========================================================================
   Pairs with design-system.css. Three independent pieces - use whichever a
   given page needs, they don't depend on each other:

     JabsSite.initSidebarToggle()
       Wires the collapsible sidebar's toggle button (id="sidebarToggle" /
       id="sidebar" in the markup design-system.css expects).

     JabsSite.initStepWalkthrough(steps)
       Wires the numbered step-pill + highlight-overlay walkthrough used by
       the JABS GUI mockup. `steps` is an array of
       { region, title, body } objects, in click order - `region` must match
       a .hl-region[data-region="..."] element's data-region attribute
       somewhere on the page. Requires #stepPills and a
       .step-detail containing #stepDetailN / #stepDetailTotal /
       #stepDetailTitle / #stepDetailBody (see either existing template page
       for the exact markup shape).

     JabsSite.initScrollSpyNav()
       For a single-page, anchor-based sidebar nav (.sidebar-nav a[href="#..."])
       - highlights the link matching whichever section is currently in view.
       Only meaningful on a single scrolling page; a multi-page site should
       mark the current page's nav link "active" server-side/at-build-time
       instead and skip this.

     JabsSite.initScrollToTop()
       Injects a fixed "scroll to top" button (no markup needed in the page
       itself), visible once the reader has scrolled past the hero.
   ========================================================================== */

var JabsSite = (function () {
  "use strict";

  function initSidebarToggle() {
    var sidebar = document.getElementById("sidebar");
    var toggle = document.getElementById("sidebarToggle");
    if (!sidebar || !toggle) return;
    toggle.addEventListener("click", function () {
      var collapsed = sidebar.classList.toggle("collapsed");
      toggle.textContent = collapsed ? "›" : "‹"; // › / ‹
    });
  }

  function initStepWalkthrough(steps) {
    var pillsEl = document.getElementById("stepPills");
    if (!pillsEl || !steps || !steps.length) return;
    var hintEl = pillsEl.querySelector(".hint");

    var regions = {};
    document.querySelectorAll(".hl-region[data-region]").forEach(function (el) {
      regions[el.getAttribute("data-region")] = el;
    });

    var totalEl = document.getElementById("stepDetailTotal");
    if (totalEl) totalEl.textContent = String(steps.length);

    var pills = steps.map(function (step, i) {
      var btn = document.createElement("button");
      btn.className = "step-pill";
      btn.type = "button";
      btn.textContent = String(i + 1);
      btn.addEventListener("click", function () { setActiveStep(i); });
      pillsEl.insertBefore(btn, hintEl || null);
      return btn;
    });

    function setActiveStep(index) {
      var step = steps[index];
      pills.forEach(function (btn, i) { btn.classList.toggle("active", i === index); });
      Object.keys(regions).forEach(function (key) {
        regions[key].classList.toggle("hl-active", key === step.region);
      });
      var setText = function (id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = text;
      };
      setText("stepDetailN", String(index + 1));
      setText("stepDetailTitle", step.title);
      setText("stepDetailBody", step.body);
    }

    setActiveStep(0);
    return { setActiveStep: setActiveStep };
  }

  function initScrollSpyNav() {
    var navLinks = Array.prototype.slice.call(document.querySelectorAll(".sidebar-nav a"));
    if (!navLinks.length || !("IntersectionObserver" in window)) return;

    var sections = navLinks
      .map(function (a) {
        var href = a.getAttribute("href") || "";
        return href.charAt(0) === "#" ? document.getElementById(href.slice(1)) : null;
      })
      .filter(Boolean);

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var id = entry.target.id;
        navLinks.forEach(function (a) {
          a.classList.toggle("active", a.getAttribute("href") === "#" + id);
        });
      });
    }, { rootMargin: "-40% 0px -55% 0px" });

    sections.forEach(function (s) { observer.observe(s); });
  }

  function initScrollToTop() {
    var btn = document.createElement("button");
    btn.className = "scroll-top-btn";
    btn.type = "button";
    btn.setAttribute("aria-label", "Scroll to top");
    btn.innerHTML = "&uarr;";
    document.body.appendChild(btn);

    function updateVisibility() {
      btn.classList.toggle("visible", window.scrollY > 400);
    }
    window.addEventListener("scroll", updateVisibility, { passive: true });
    updateVisibility();

    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  return {
    initSidebarToggle: initSidebarToggle,
    initStepWalkthrough: initStepWalkthrough,
    initScrollSpyNav: initScrollSpyNav,
    initScrollToTop: initScrollToTop,
  };
})();
