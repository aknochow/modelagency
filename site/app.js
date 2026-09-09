const state = { records: [], recommendations: {}, sort: "score", direction: "desc" };

const escapeHtml = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
}[char]));

const agentLabel = (row) => row.agent_id || "model-level";

function filterValues(key) {
  return [...new Set(state.records.map((row) => key === "agent_id" ? agentLabel(row) : row[key]))].filter(Boolean).sort();
}

function enabledValues(storageKey, values) {
  const stored = JSON.parse(localStorage.getItem(storageKey) || "null");
  return new Set(Array.isArray(stored) ? stored.filter((value) => values.includes(value)) : values);
}

function makeFilter(containerId, values, storageKey, labelFor) {
  const container = document.querySelector(`#${containerId}`);
  const enabled = enabledValues(storageKey, values);
  container.innerHTML = values.map((value, index) => `<label class="check"><input type="checkbox" data-filter-value="${escapeHtml(value)}" id="${containerId}-${index}" ${enabled.has(value) ? "checked" : ""}>${escapeHtml(labelFor(value))}</label>`).join("");
  container.querySelectorAll("input").forEach((input) => input.addEventListener("change", () => {
    const selected = [...container.querySelectorAll("input:checked")].map((item) => item.dataset.filterValue);
    localStorage.setItem(storageKey, JSON.stringify(selected));
    render();
  }));
}

function selectedValues(containerId) {
  return new Set([...document.querySelectorAll(`#${containerId} input:checked`)].map((input) => input.dataset.filterValue));
}

function renderRecommendations() {
  const container = document.querySelector("#suggestions");
  const visibleModels = selectedValues("model-filters");
  const visibleAgents = selectedValues("agent-filters");
  const cards = Object.entries(state.recommendations).filter(([, entries]) => {
    return Object.values(entries).some((row) => row && visibleModels.has(row.model_name) && visibleAgents.has(row.agent_id || "model-level"));
  }).map(([category, entries]) => {
    const lines = Object.entries(entries).map(([label, row]) => {
      if (!row || !visibleModels.has(row.model_name) || !visibleAgents.has(row.agent_id || "model-level")) return "";
      const taskCost = row.cost_per_task_usd === null ? "task cost unavailable" : `$${Number(row.cost_per_task_usd).toFixed(4)}/task`;
      return `<li><strong>${escapeHtml(label.replaceAll("_", " "))}</strong>: ${escapeHtml(row.model_name)} — ${escapeHtml(row.score)} ${escapeHtml(row.score_unit)}; ${taskCost}; <a href="${escapeHtml(row.evidence_url)}">evidence</a>${row.original_source_url ? ` · <a href="${escapeHtml(row.original_source_url)}">original</a>` : ""}</li>`;
    }).filter(Boolean).join("");
    return `<article class="card"><h3>${escapeHtml(category.replaceAll("_", " "))}</h3><ul>${lines || "<li>No visible recommendation</li>"}</ul></article>`;
  });
  container.innerHTML = cards.join("") || "<p class=\"muted\">No recommendations match the enabled models and agents.</p>";
}

function render() {
  const search = document.querySelector("#search").value.trim().toLowerCase();
  const category = document.querySelector("#category").value;
  const pricedOnly = document.querySelector("#priced-only").checked;
  const models = selectedValues("model-filters");
  const agents = selectedValues("agent-filters");
  const rows = state.records.filter((row) => {
    const text = [row.model_name, row.provider, row.category, row.benchmark_id].join(" ").toLowerCase();
    return (!search || text.includes(search)) && (!category || row.category === category) && (!pricedOnly || row.cost_per_task_usd !== null) && models.has(row.model_name) && agents.has(agentLabel(row));
  }).sort((left, right) => {
    const a = left[state.sort]; const b = right[state.sort];
    if (a === b) return 0;
    if (a === null || a === undefined) return 1;
    if (b === null || b === undefined) return -1;
    const result = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b));
    return state.direction === "asc" ? result : -result;
  });
  document.querySelector("#status").textContent = `${rows.length} of ${state.records.length} records`;
  document.querySelector("#results").innerHTML = rows.map((row) => `<tr>
    <td>${escapeHtml(row.model_name)}</td>
    <td>${escapeHtml(row.provider)}</td>
    <td>${escapeHtml(row.category)}</td>
    <td>${escapeHtml(row.benchmark_id)} <small>${escapeHtml(row.benchmark_version)}</small></td>
    <td>${escapeHtml(row.score)} ${escapeHtml(row.score_unit)}</td>
    <td>${row.cost_per_task_usd === null ? "—" : `$${Number(row.cost_per_task_usd).toFixed(4)}`}</td>
    <td>${row.input_price_per_million_usd === null || row.output_price_per_million_usd === null ? "—" : `$${Number(row.input_price_per_million_usd).toFixed(2)} / $${Number(row.output_price_per_million_usd).toFixed(2)} per 1M`}</td>
    <td><a href="${escapeHtml(row.evidence_url)}" rel="noreferrer">evidence</a>${row.original_source_url ? ` · <a href="${escapeHtml(row.original_source_url)}" rel="noreferrer">original</a>` : ""}<br><small>${escapeHtml(row.attribution)}</small></td>
  </tr>`).join("");
  renderRecommendations();
}

fetch("data/results.json").then((response) => response.json()).then((payload) => {
  state.records = payload.records || [];
  state.recommendations = payload.recommendations || {};
  [...new Set(state.records.map((row) => row.category))].sort().forEach((category) => {
    const option = document.createElement("option"); option.value = category; option.textContent = category.replaceAll("_", " ");
    document.querySelector("#category").append(option);
  });
  makeFilter("model-filters", filterValues("model_name"), "modelagency-enabled-models", (value) => value);
  makeFilter("agent-filters", filterValues("agent_id"), "modelagency-enabled-agents", (value) => value);
  render();
}).catch((error) => {
  document.querySelector("#status").textContent = `Unable to load generated data: ${error}`;
});

["#search", "#category", "#priced-only"].forEach((selector) => document.querySelector(selector).addEventListener("input", render));
document.querySelectorAll("[data-sort]").forEach((button) => button.addEventListener("click", () => {
  const sort = button.dataset.sort;
  state.direction = state.sort === sort && state.direction === "desc" ? "asc" : "desc";
  state.sort = sort;
  render();
}));
