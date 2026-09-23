(() => {
  const footer = document.querySelector("[data-site-footer]");
  if (!footer) return;

  fetch("data/build.json", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error(`Build metadata request failed: ${response.status}`);
      return response.json();
    })
    .then((metadata) => {
      const version = String(metadata.version || "v.alpha");
      const buildDate = String(metadata.build_date || "");
      footer.querySelector("[data-site-version]").textContent = version;
      const date = footer.querySelector("[data-site-build-date]");
      if (buildDate) {
        date.textContent = buildDate;
        date.dateTime = buildDate;
      }
    })
    .catch(() => {
      // Keep the static alpha/version fallback when metadata is unavailable.
    });
})();
