fetch("data/results.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then((payload) => {
    if (payload.source_context?.attribution) {
      document.querySelector("#source-attribution").textContent = payload.source_context.attribution;
    }
  })
  .catch(() => {
    document.querySelector("#source-attribution").textContent = "Benchmark data from BenchLM.ai under its MIT dataset license. Snapshot retrieval date is unavailable; original benchmark publishers retain their attribution.";
  });
