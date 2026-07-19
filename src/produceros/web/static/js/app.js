// ProducerOS client-side behavior. Minimal vanilla JS, no build step, no
// external libraries. Progressive enhancement only -- every page must
// still work with JS disabled for its core server-rendered form.

(function () {
  "use strict";

  function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(function () {
        // Offline shell simply won't be available; the live app still works.
      });
    }
  }

  function updateOfflineIndicator() {
    document.body.classList.toggle("is-offline", !navigator.onLine);
  }

  function initFilterDrawer() {
    var toggles = document.querySelectorAll("[data-filter-toggle]");
    var drawer = document.querySelector("[data-filter-drawer]");
    if (!drawer) return;
    toggles.forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        drawer.classList.toggle("open");
      });
    });
    var closeBtn = drawer.querySelector("[data-filter-close]");
    if (closeBtn) closeBtn.addEventListener("click", function () { drawer.classList.remove("open"); });
    drawer.addEventListener("click", function (event) {
      if (event.target === drawer) drawer.classList.remove("open");
    });
  }

  function initConfirmForms() {
    document.querySelectorAll("[data-confirm]").forEach(function (el) {
      el.addEventListener("submit", function (event) {
        var message = el.getAttribute("data-confirm");
        if (!window.confirm(message)) {
          event.preventDefault();
        }
      });
    });
  }

  function initExpandableCards() {
    document.querySelectorAll("[data-expand-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var targetId = btn.getAttribute("data-expand-toggle");
        var target = document.getElementById(targetId);
        if (!target) return;
        var isOpen = target.classList.toggle("open");
        btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
      });
    });
  }

  function initDashboardCache() {
    // Cache the last dashboard summary for the offline app shell (spec 17).
    var summaryEl = document.querySelector("[data-dashboard-summary]");
    if (summaryEl && "localStorage" in window) {
      try {
        localStorage.setItem("produceros:last-dashboard", summaryEl.innerHTML);
        localStorage.setItem("produceros:last-dashboard-at", new Date().toISOString());
      } catch (e) {
        /* storage unavailable; not fatal */
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    registerServiceWorker();
    updateOfflineIndicator();
    window.addEventListener("online", updateOfflineIndicator);
    window.addEventListener("offline", updateOfflineIndicator);
    initFilterDrawer();
    initConfirmForms();
    initExpandableCards();
    initDashboardCache();
  });
})();
