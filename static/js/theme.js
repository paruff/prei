/**
 * Dark mode toggle — client-side only (localStorage).
 *
 * Supported values: "light", "dark", "system".
 * Defaults to "system" (follows OS preference via prefers-color-scheme).
 * Stores selection in localStorage key "prei-theme".
 */
(function () {
  const STORAGE_KEY = "prei-theme";
  const THEMES = ["light", "dark", "system"];

  /** Read saved theme or default to "system". */
  function getSavedTheme() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return THEMES.includes(saved) ? saved : "system";
    } catch {
      return "system";
    }
  }

  /** Resolve "system" to the actual OS preference. */
  function resolveTheme(theme) {
    if (theme === "system") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return theme;
  }

  /** Apply theme to the document and update toggle button icon. */
  function applyTheme(theme) {
    const resolved = resolveTheme(theme);
    document.documentElement.setAttribute("data-bs-theme", resolved);
    updateToggleIcon(resolved);
  }

  /** Update the sun/moon icon on the toggle button. */
  function updateToggleIcon(resolvedTheme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    const icon = btn.querySelector(".theme-icon");
    if (!icon) return;
    // Use moon when light, sun when dark
    icon.textContent = resolvedTheme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19";
    // Update aria-label
    btn.setAttribute(
      "aria-label",
      resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"
    );
  }

  /** Cycle through light → dark → system. */
  function cycleTheme() {
    const current = getSavedTheme();
    const next =
      current === "light" ? "dark" : current === "dark" ? "system" : "light";
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // localStorage full or blocked — ignore
    }
    applyTheme(next);
    updateCycleLabel(next);
    updateActiveState(next);
  }

  /** Update the dropdown label to show current mode. */
  function updateCycleLabel(theme) {
    const label = document.getElementById("theme-label");
    if (label) {
      const labels = { light: "Light", dark: "Dark", system: "System" };
      label.textContent = labels[theme] || "System";
    }
  }

  /** Highlight the active item in the dropdown. */
  function updateActiveState(theme) {
    document.querySelectorAll("[data-theme-value]").forEach((el) => {
      el.classList.toggle("active", el.getAttribute("data-theme-value") === theme);
    });
  }

  /** Handle dropdown item clicks. */
  function initDropdown() {
    document.querySelectorAll("[data-theme-value]").forEach((el) => {
      el.addEventListener("click", function (e) {
        e.preventDefault();
        const theme = this.getAttribute("data-theme-value");
        try {
          localStorage.setItem(STORAGE_KEY, theme);
        } catch {
          // ignore
        }
        applyTheme(theme);
        updateCycleLabel(theme);
        updateActiveState(theme);
      });
    });
  }

  /** Listen for OS theme changes when in "system" mode. */
  function watchSystemPreference() {
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", () => {
        if (getSavedTheme() === "system") {
          applyTheme("system");
        }
      });
  }

  // --- Init ---
  const saved = getSavedTheme();
  applyTheme(saved);
  updateCycleLabel(saved);
  updateActiveState(saved);
  initDropdown();
  watchSystemPreference();

  // Expose toggle for the quick-switch button
  window.preiToggleTheme = cycleTheme;
})();
