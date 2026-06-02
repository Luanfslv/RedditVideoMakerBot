/* ============================================================
   RedditMaker Studio — shared UI logic (multi-page Jinja build)
   Ported from the design SPA. The data-view router and the
   sample-data arrays were removed: each page now loads its own
   real data (videos.json / backgrounds.json / config.toml) via
   its inline script. This file only owns generic, page-agnostic
   behaviours and is safe to load on every page.
   ============================================================ */
(function () {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  /* ---- lucide icons (re-callable after dynamic injection) ---- */
  function drawIcons() {
    if (window.lucide) window.lucide.createIcons();
  }
  window.drawIcons = drawIcons;
  drawIcons();

  /* ---- gradient palette for placeholder thumbnails ---- */
  const grads = [
    "linear-gradient(160deg,#3B1D78,#160F28)",
    "linear-gradient(160deg,#5B2A8C,#1A1030)",
    "linear-gradient(160deg,#2A1B52,#0F0A1C)",
    "linear-gradient(160deg,#4C2A7E,#180F2C)",
    "linear-gradient(160deg,#6D28D9,#1C1233)",
    "linear-gradient(160deg,#321E5C,#100B20)",
  ];
  window.thumbGradient = (i) => grads[((i % grads.length) + grads.length) % grads.length];

  /* ---- segmented controls (visual single-select) ---- */
  $$(".segmented").forEach((seg) => {
    seg.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      $$("button", seg).forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
    });
  });

  /* ---- choice cards (single-select within a grid) ---- */
  function bindChoiceGrids(root = document) {
    $$(".choice-grid", root).forEach((grid) => {
      if (grid.dataset.bound) return;
      grid.dataset.bound = "1";
      grid.addEventListener("click", (e) => {
        const c = e.target.closest(".choice");
        if (!c) return;
        $$(".choice", grid).forEach((x) => {
          x.classList.remove("selected");
          const chk = $(".check", x);
          if (chk) chk.remove();
        });
        c.classList.add("selected");
        const span = document.createElement("span");
        span.className = "check";
        span.innerHTML = '<i data-lucide="check"></i>';
        c.appendChild(span);
        // reflect into an optional hidden input <input data-choice-target>
        const hidden = grid.querySelector("[data-choice-target]");
        if (hidden && c.dataset.value !== undefined) hidden.value = c.dataset.value;
        drawIcons();
      });
    });
  }
  window.bindChoiceGrids = bindChoiceGrids;
  bindChoiceGrids();

  /* ---- range sliders: live value readout ---- *
   * The readout shows the RAW input value, because on the real
   * Settings page that value is exactly what gets submitted.    */
  function bindRanges(root = document) {
    $$(".range", root).forEach((r) => {
      const val = r.parentElement.querySelector(".range-val");
      if (!val || r.dataset.bound) return;
      r.dataset.bound = "1";
      const fmt = () => {
        val.textContent = r.value;
      };
      r.addEventListener("input", fmt);
      fmt();
    });
  }
  window.bindRanges = bindRanges;
  bindRanges();

  /* ---- modal: generic open/close ----
   *  open  : any element with [data-modal-open="#modalId"]
   *  close : click on the overlay itself or any [data-close]   */
  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-modal-open]");
    if (opener) {
      const m = $(opener.getAttribute("data-modal-open"));
      if (m) m.classList.add("open");
      return;
    }
    const overlay = e.target.closest(".modal-overlay");
    if (overlay && (e.target === overlay || e.target.closest("[data-close]"))) {
      overlay.classList.remove("open");
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") $$(".modal-overlay.open").forEach((m) => m.classList.remove("open"));
  });

  /* ---- toast ---- */
  const toast = $("#toast");
  const toastMsg = $("#toastMsg");
  let toastTimer;
  window.showToast = function (msg) {
    if (!toast) return;
    if (toastMsg) toastMsg.textContent = msg;
    toast.style.transform = "translate(-50%, 0)";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.style.transform = "translate(-50%, 140%)";
    }, 2600);
  };

  /* ---- spin keyframes (used by loading buttons), inject once ---- */
  const st = document.createElement("style");
  st.textContent = "@keyframes spin{to{transform:rotate(360deg)}}.spin{animation:spin 1s linear infinite}";
  document.head.appendChild(st);
})();
