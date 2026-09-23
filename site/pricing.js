const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
}[character]));

const safeHref = (value) => /^https:\/\//i.test(String(value || "")) ? escapeHtml(value) : "#";

function formatPrice(value) {
  if (value === null || value === undefined || value === "") return "Not published in this snapshot";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "Not published in this snapshot";
  if (amount > 0 && amount < 0.01) return "<$0.01";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 4, minimumFractionDigits: 0 });
}

function checkedDate(payload) {
  const dates = [
    ...(payload.records || []).map((row) => row.retrieved_date),
    ...(payload.roster_pricing?.records || []).map((row) => row.retrieved_date),
    payload.roster_pricing?.retrieved_date,
    payload.source_context?.retrieved_date
  ]
    .filter(Boolean)
    .sort();
  return dates.length ? dates[dates.length - 1] : "unavailable";
}

function renderPricing(payload) {
  const container = document.querySelector("#pricing-page");
  const rows = [...(payload.model_summaries || [])];
  const summaryIds = new Set(rows.map((row) => row.configuration_id || row.model_id));
  (payload.roster_pricing?.records || []).forEach((row) => {
    if (summaryIds.has(row.model_id)) return;
    rows.push({
      ...row,
      configuration_id: row.model_id,
      pricing_notes: row.notes || ""
    });
  });
  const date = checkedDate(payload);
  const groups = new Map();
  rows.forEach((row) => {
    const provider = row.provider || "Unknown provider";
    if (!groups.has(provider)) groups.set(provider, { provider, source: row.pricing_source_url || "", rows: [] });
    const group = groups.get(provider);
    if (!group.source && row.pricing_source_url) group.source = row.pricing_source_url;
    group.rows.push(row);
  });
  const providers = [...groups.values()].sort((left, right) => left.provider.localeCompare(right.provider)).map((group) => {
    const providerSlug = group.provider.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "unknown-provider";
    const source = group.source
      ? `<a href="${safeHref(group.source)}" target="_blank" rel="noreferrer">${escapeHtml(group.source)} ↗</a>`
      : "Pricing source unavailable";
    const models = group.rows.sort((left, right) => left.model_name.localeCompare(right.model_name)).map((row) => {
      const input = formatPrice(row.input_price_per_million_usd);
      const output = formatPrice(row.output_price_per_million_usd);
      const variant = row.pricing_variant ? ` <small class="pricing-variant">${escapeHtml(row.pricing_variant)}</small>` : "";
      const notes = row.pricing_notes || row.notes;
      const noteCell = notes ? `<small class="pricing-note">${escapeHtml(notes)}</small>` : "";
      return `<tr><th scope="row">${escapeHtml(row.model_name)}${variant}${noteCell}</th><td>${escapeHtml(row.configuration_id || row.model_id)}</td><td>${escapeHtml(input)}</td><td>${escapeHtml(output)}</td></tr>`;
    }).join("");
    return `<section class="pricing-provider" id="pricing-${providerSlug}" aria-labelledby="pricing-${providerSlug}-heading"><h3 id="pricing-${providerSlug}-heading">${escapeHtml(group.provider)}</h3><p class="pricing-provider-meta">Checked ${escapeHtml(date)} · ${source}</p><div class="table-wrap"><table class="canonical-table pricing-table"><caption class="sr-only">${escapeHtml(group.provider)} token prices per 1M tokens</caption><thead><tr><th scope="col">Model</th><th scope="col">Model slug</th><th scope="col">Input / 1M</th><th scope="col">Output / 1M</th></tr></thead><tbody>${models}</tbody></table></div></section>`;
  }).join("");
  document.querySelector("#pricing-attribution").innerHTML = `Snapshot prices checked ${escapeHtml(date)}. Prices are estimates, not subscription rates or measured task costs.`;
  container.innerHTML = providers || '<p class="muted">No token pricing records are available in this snapshot.</p>';
}

fetch("data/results.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(renderPricing)
  .catch(() => {
    document.querySelector("#pricing-attribution").textContent = "The pricing snapshot could not be loaded.";
    document.querySelector("#pricing-page").innerHTML = '<p class="error">Pricing is unavailable in this snapshot.</p>';
  });
