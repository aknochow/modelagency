(() => {
  const STORAGE_KEY = "modelagency-theme-v1";
  const modes = new Set(["system", "light", "dark"]);
  const root = document.documentElement;
  const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  let mode = "system";

  function normalize(value) {
    return modes.has(value) ? value : "system";
  }

  function systemIsDark() {
    return Boolean(media && media.matches);
  }

  function apply(nextMode, persist = false) {
    mode = normalize(nextMode);
    const dark = mode === "dark" || (mode === "system" && systemIsDark());
    root.classList.toggle("pf-v6-theme-dark", dark);
    root.dataset.theme = mode;
    root.style.colorScheme = dark ? "dark" : "light";
    const select = document.querySelector("#theme-mode");
    if (select && select.value !== mode) select.value = mode;
    if (persist) {
      try {
        localStorage.setItem(STORAGE_KEY, mode);
      } catch (_error) {
      }
    }
  }

  try {
    mode = normalize(localStorage.getItem(STORAGE_KEY));
  } catch (_error) {
    mode = "system";
  }
  apply(mode);

  function initialize() {
    const select = document.querySelector("#theme-mode");
    if (select) select.addEventListener("change", () => apply(select.value, true));
    if (media) {
      const updateSystemTheme = () => {
        if (mode === "system") apply("system");
      };
      if (media.addEventListener) media.addEventListener("change", updateSystemTheme);
      else if (media.addListener) media.addListener(updateSystemTheme);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
