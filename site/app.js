const DOMAIN_COLUMNS = [
  ["engineering", "Engineering"],
  ["management", "Management"],
  ["media", "Media"]
];
const DOMAIN_CATEGORIES = {
  engineering: ["coding", "terminal", "cicd"],
  management: ["administrative", "office", "computer_use"],
  media: ["graphics", "visual_reasoning", "writing"]
};
const DAILY_DRIVER_CATEGORY = "daily_driver";
const DAILY_DRIVER_CATEGORY_COUNT = 8;
const DAILY_DRIVER_MIN_COVERAGE = Math.ceil(DAILY_DRIVER_CATEGORY_COUNT / 2);
const PORTFOLIO_OPTION_COUNT = 2;
const PORTFOLIO_TIER_ORDER = { value: 1, balanced: 2, premium: 3 };
const BENCHLM_METRIC_FIELDS = [
  ["benchlm_agentic", "Agentic score"],
  ["terminal_bench_2", "Terminal-Bench 2.0"],
  ["browsecomp", "BrowseComp"],
  ["osworld_verified", "OSWorld-Verified"],
  ["benchlm_overall", "Overall"]
];
const DOMAIN_DESCRIPTIONS = {
  engineering: "Coding, terminal, and CI/CD workflows.",
  management: "Administrative, office, and interactive computer tasks.",
  media: "Graphics, visual reasoning, and writing.",
  [DAILY_DRIVER_CATEGORY]: "Cross-work fit; BenchLM score."
};
const PORTFOLIO_ALLOCATIONS = [
  { key: "specialist", label: "Specialist work", share: 0.10, tier: "premium", description: "Reserve the strongest model for the hardest tasks." },
  { key: "balanced", label: "Everyday work", share: 0.30, tier: "balanced", description: "Use a capable middle tier for routine work." },
  { key: "volume", label: "High-volume work", share: 0.60, tier: "value", description: "Keep the majority of work on the economical tier." }
];
const MODEL_ROSTER = {
  "gpt-6-astra": "GPT-6 Astra",
  "composer-2-5": "Composer 2.5 (Cursor)",
  "gemini-3-1-pro": "Gemini 3.1 Pro"
};
const MODEL_ROSTER_PROVIDERS = {
  "gpt-6-astra": "OpenAI",
  "composer-2-5": "Cursor",
  "gemini-3-1-pro": "Google"
};
const SORTABLE_FIELDS = ["model_name", "provider", ...BENCHLM_METRIC_FIELDS.map(([key]) => key), ...DOMAIN_COLUMNS.map(([key]) => key), "daily_driver", "cost_tier", "monthly_cost"];
const BENCHLM_DEFAULT_SORT = "benchlm_overall";
const BUDGET_DEFAULTS = { monthly_budget_usd: 300, monthly_input_tokens: 20000000, monthly_output_tokens: 5000000 };
const BUDGET_UNLIMITED = 5000;
const VIEW_STORAGE_KEY = "modelagency-view-v1";
const ROSTER_MIGRATION_KEY = "modelagency-roster-gpt-6-astra-v1";
const COMPOSER_ROSTER_MIGRATION_KEY = "modelagency-roster-composer-2-5-v1";
const GEMINI_PRO_ROSTER_MIGRATION_KEY = "modelagency-roster-gemini-3-1-pro-v1";
const DEFAULT_VIEW = {
  version: 1,
  models: [
    "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5",
    "gpt-5-6-luna", "gpt-5-6-sol", "gpt-5-6-terra", "gpt-6-astra",
    "gemini-3-6-flash", "grok-4-6", "composer-2-5", "gemini-3-1-pro"
  ],
  agents: ["model-level"],
  search: "",
  category: "",
  sort: "benchlm_agentic",
  direction: "desc",
  ...BUDGET_DEFAULTS
};
const state = {
  records: [],
  summaries: [],
  sourceContext: {},
  leaderboard: { status: "unavailable", records: [] },
  benchlmMetrics: { status: "unavailable", records: [] },
  rosterPricing: { status: "unavailable", records: [] },
  defaultView: DEFAULT_VIEW,
  view: null,
  sort: "daily_driver",
  direction: "desc",
  benchlmSort: BENCHLM_DEFAULT_SORT,
  benchlmDirection: "desc"
};

const escapeHtml = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
}[char]));

const safeHref = (value) => /^https:\/\//i.test(String(value || "")) ? escapeHtml(value) : "#";
const agentLabel = (row) => row.agent_id || "model-level";
const modelFilterId = (row) => String(row.configuration_id || row.model_id || "").replace(/:daily-driver$/, "");
const uniqueStrings = (values) => [...new Set((Array.isArray(values) ? values : []).map(String).map((value) => value.trim()).filter(Boolean))];

function normalizeView(view) {
  const source = view && typeof view === "object" ? view : {};
  const budget = {};
  for (const [field, fallback] of Object.entries(BUDGET_DEFAULTS)) {
    const raw = source[field] === undefined ? fallback : source[field];
    const value = typeof raw === "string" && /^\d+$/.test(raw) ? Number(raw) : raw;
    const maximum = field === "monthly_budget_usd" ? BUDGET_UNLIMITED : 1000000000;
    if (!Number.isInteger(value) || value < 0 || value > maximum) throw new Error(`${field} must be a whole number from 0 to ${maximum}`);
    budget[field] = value;
  }
  return {
    version: 1,
    models: uniqueStrings(source.models),
    agents: uniqueStrings(source.agents),
    search: String(source.search || ""),
    category: String(source.category || ""),
    sort: SORTABLE_FIELDS.includes(source.sort) ? source.sort : "daily_driver",
    direction: source.direction === "asc" ? "asc" : "desc",
    ...budget
  };
}

function readStoredView(fallback) {
  try {
    const stored = localStorage.getItem(VIEW_STORAGE_KEY);
    if (stored) {
      const view = normalizeView(JSON.parse(stored));
      // Add newly available work models once to an existing non-empty view;
      // later manual unchecks remain persistent.
      if (view.models.length && !localStorage.getItem(ROSTER_MIGRATION_KEY)) {
        view.models = uniqueStrings([...view.models, "gpt-6-astra"]);
        try {
          localStorage.setItem(ROSTER_MIGRATION_KEY, "1");
        } catch (_error) {
          // The view still receives Astra for this session if storage is full or unavailable.
        }
      }
      if (view.models.length && !localStorage.getItem(COMPOSER_ROSTER_MIGRATION_KEY)) {
        view.models = uniqueStrings([...view.models, "composer-2-5"]);
        try {
          localStorage.setItem(COMPOSER_ROSTER_MIGRATION_KEY, "1");
        } catch (_error) {
          // The view still receives Composer for this session if storage is unavailable.
        }
      }
      if (view.models.length && !localStorage.getItem(GEMINI_PRO_ROSTER_MIGRATION_KEY)) {
        view.models = uniqueStrings([...view.models, "gemini-3-1-pro"]);
        try {
          localStorage.setItem(GEMINI_PRO_ROSTER_MIGRATION_KEY, "1");
        } catch (_error) {
          // The view still receives Gemini 3.1 Pro for this session if storage is unavailable.
        }
      }
      return view;
    }

    // Migrate the first prototype's separate filter keys when present.
    const oldModels = JSON.parse(localStorage.getItem("modelagency-enabled-models") || "null");
    const oldAgents = JSON.parse(localStorage.getItem("modelagency-enabled-agents") || "null");
    if (Array.isArray(oldModels) || Array.isArray(oldAgents)) {
      return normalizeView({
        ...fallback,
        models: Array.isArray(oldModels) ? oldModels : fallback.models,
        agents: Array.isArray(oldAgents) ? oldAgents : fallback.agents
      });
    }
  } catch (_error) {
    // Private browsing or disabled storage should not make the dashboard fail.
  }
  return normalizeView(fallback);
}

function saveView() {
  if (!state.view) return;
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify(state.view));
  } catch (_error) {
    // The view still works for the current tab when persistent storage is unavailable.
  }
  const yaml = document.querySelector("#view-yaml");
  if (yaml) yaml.value = dumpView(state.view);
}

function filterValues(key) {
  const values = state.records.map((row) => key === "agent_id" ? agentLabel(row) : key === "model_id" ? modelFilterId(row) : row[key]);
  if (key === "model_id") values.push(...Object.keys(MODEL_ROSTER), ...state.leaderboard.records.map(modelFilterId), ...state.benchlmMetrics.records.map(modelFilterId));
  return [...new Set(values)]
    .filter(Boolean)
    .sort((left, right) => String(left).localeCompare(String(right)));
}

function modelOptionIds() {
  return new Set([
    ...state.summaries.map(modelFilterId),
    ...Object.keys(MODEL_ROSTER),
    ...state.leaderboard.records.map(modelFilterId),
    ...state.benchlmMetrics.records.map(modelFilterId)
  ]);
}

function comparisonModelCount() {
  return modelOptionIds().size;
}

function modelDisplayName(modelId) {
  const row = state.records.find((candidate) => modelFilterId(candidate) === modelId)
    || state.leaderboard.records.find((candidate) => modelFilterId(candidate) === modelId);
  const displayName = row ? row.configuration_label || row.model_name : MODEL_ROSTER[modelId] || modelId;
  return `${displayName} (${modelId})`;
}

function canonicalizeModelIds(values) {
  const idsByName = new Map();
  state.records.forEach((row) => {
    if (!idsByName.has(row.model_name)) idsByName.set(row.model_name, modelFilterId(row));
  });
  Object.entries(MODEL_ROSTER).forEach(([modelId, displayName]) => {
    if (!idsByName.has(displayName)) idsByName.set(displayName, modelId);
  });
  return uniqueStrings(values).map((value) => idsByName.get(value) || value);
}

function canonicalizeView(view) {
  const normalized = normalizeView(view);
  normalized.models = uniqueStrings(canonicalizeModelIds(normalized.models));
  return normalized;
}

function selectedValues(containerId) {
  return new Set([...document.querySelectorAll(`#${containerId} input:checked`)].map((input) => input.dataset.filterValue));
}

function selectedModelCount() {
  return selectedValues("model-filters").size;
}

function selectedAgentValues() {
  return new Set(["model-level"]);
}

function makeFilter(containerId, values, selected, labelFor) {
  const container = document.querySelector(`#${containerId}`);
  const enabled = new Set(selected);
  container.innerHTML = values.map((value, index) => `<label class="check">
    <input type="checkbox" data-filter-value="${escapeHtml(value)}" id="${containerId}-${index}" ${enabled.has(value) ? "checked" : ""}>
    <span>${escapeHtml(labelFor(value))}</span>
  </label>`).join("");
  container.querySelectorAll("input").forEach((input) => input.addEventListener("change", () => {
    syncViewFromControls();
    saveView();
    render();
  }));
}

function syncViewFromControls() {
  if (!state.view) return;
  state.view.models = [...selectedValues("model-filters")];
  state.view.agents = ["model-level"];
  state.view.search = document.querySelector("#search").value;
  state.view.category = "";
  state.view.sort = state.sort;
  state.view.direction = state.direction;
  state.view.monthly_budget_usd = Number(document.querySelector("#monthly-budget").value);
  syncBudgetAmount();
}

function applyViewToControls() {
  if (!state.view) return;
  document.querySelector("#search").value = state.view.search;
  document.querySelector("#monthly-budget").value = state.view.monthly_budget_usd;
  syncBudgetAmount();
  document.querySelector("#monthly-input-million").value = state.view.monthly_input_tokens / 1000000;
  document.querySelector("#monthly-output-million").value = state.view.monthly_output_tokens / 1000000;
  document.querySelector("#budget-error").textContent = "";
  state.sort = state.view.sort;
  state.direction = state.view.direction;
  document.querySelectorAll("#model-filters input").forEach((input) => {
    input.checked = state.view.models.includes(input.dataset.filterValue);
  });
}

function formatYamlScalar(value) {
  return JSON.stringify(String(value));
}

function dumpView(view, includeAttribution = false) {
  const normalized = normalizeView(view);
  const lines = includeAttribution ? [
    `# ${state.sourceContext.attribution || "Benchmark data from BenchLM.ai; retrieval date unavailable."}`,
    "# https://benchlm.ai/data · Canonical leaderboard: https://benchlm.ai/llm-agent-benchmarks",
    "# Daily Driver, work domains, and value are derived by modelagency."
  ] : [];
  lines.push("version: 1", "models:");
  normalized.models.forEach((model) => lines.push(`  - ${formatYamlScalar(model)}`));
  lines.push("agents:");
  normalized.agents.forEach((agent) => lines.push(`  - ${formatYamlScalar(agent)}`));
  lines.push(`search: ${formatYamlScalar(normalized.search)}`);
  lines.push(`category: ${formatYamlScalar(normalized.category)}`);
  lines.push(`sort: ${formatYamlScalar(normalized.sort)}`);
  lines.push(`direction: ${formatYamlScalar(normalized.direction)}`);
  Object.keys(BUDGET_DEFAULTS).forEach((field) => lines.push(`${field}: ${normalized[field]}`));
  return `${lines.join("\n")}\n`;
}

function parseYamlScalar(value) {
  const trimmed = value.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed.startsWith('"') && trimmed.endsWith('"')) return JSON.parse(trimmed);
  if (trimmed.startsWith("'") && trimmed.endsWith("'")) return trimmed.slice(1, -1);
  return trimmed;
}

function parseViewYaml(text) {
  const result = {};
  let currentList = null;
  for (const rawLine of String(text).split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("- ")) {
      if (!currentList) throw new Error("YAML list item has no key");
      result[currentList].push(parseYamlScalar(line.slice(2)));
      continue;
    }
    const separator = line.indexOf(":");
    if (separator < 0) throw new Error(`Unsupported YAML line: ${rawLine}`);
    const key = line.slice(0, separator).trim();
    const rawValue = line.slice(separator + 1).trim();
    if (rawValue) {
      result[key] = parseYamlScalar(rawValue);
      currentList = null;
    } else {
      result[key] = [];
      currentList = key;
    }
  }
  return normalizeView(result);
}

function setViewStatus(message, isError = false) {
  const status = document.querySelector("#view-status");
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function applyYaml() {
  try {
    state.view = canonicalizeView(parseViewYaml(document.querySelector("#view-yaml").value));
    applyViewToControls();
    saveView();
    render();
    setViewStatus("View applied and saved.");
  } catch (error) {
    setViewStatus(`YAML not applied: ${error.message}`, true);
  }
}

function exportYaml() {
  syncViewFromControls();
  saveView();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([dumpView(state.view, true)], { type: "text/yaml" }));
  link.download = "modelagency-view.yaml";
  link.click();
  URL.revokeObjectURL(link.href);
  setViewStatus("YAML exported.");
}

function setAllFilters(containerId, checked) {
  document.querySelectorAll(`#${containerId} input`).forEach((input) => { input.checked = checked; });
  syncViewFromControls();
  saveView();
  render();
}

function formatLabel(value) {
  return String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function monthlyCost(row) {
  const input = row.input_price_per_million_usd;
  const output = row.output_price_per_million_usd;
  if (!Number.isFinite(input) || !Number.isFinite(output) || input < 0 || output < 0) return null;
  const view = state.view || DEFAULT_VIEW;
  return view.monthly_input_tokens / 1000000 * input + view.monthly_output_tokens / 1000000 * output;
}

function rosterPricingRecord(modelId) {
  return (state.rosterPricing.records || []).find((record) => record.model_id === modelId) || null;
}

function benchlmMetricRecord(rowOrModelId) {
  const modelId = typeof rowOrModelId === "string" ? rowOrModelId : rowOrModelId?.model_id;
  return (state.benchlmMetrics.records || []).find((record) => record.model_id === modelId) || null;
}

function benchlmMetricValue(row, field) {
  const record = benchlmMetricRecord(row);
  if (!record) return null;
  if (field === "benchlm_agentic") return Number.isFinite(record.agentic_score) ? record.agentic_score : null;
  if (field === "benchlm_overall") return Number.isFinite(record.overall_score) ? record.overall_score : null;
  const metric = record.benchmarks?.[field];
  return metric && Number.isFinite(metric.score) ? metric.score : null;
}

function metricEvidenceUrl(row, field) {
  const record = benchlmMetricRecord(row);
  if (!record) return null;
  if (field === "benchlm_agentic") return record.agentic_score === null ? null : "https://benchlm.ai/llm-agent-benchmarks";
  if (field === "benchlm_overall") return record.overall_score === null ? null : "https://benchlm.ai/";
  return record.benchmarks?.[field]?.score === null ? null : record.benchmarks?.[field]?.evidence_url;
}

function formatMetric(value, decimals = 1) {
  if (!Number.isFinite(value)) return "—";
  return Number(value).toFixed(decimals);
}

function metricCell(row, field, decimals = 1) {
  const value = benchlmMetricValue(row, field);
  const url = metricEvidenceUrl(row, field);
  const text = formatMetric(value, decimals);
  return url && text !== "—"
    ? `<a href="${safeHref(url)}" target="_blank" rel="noreferrer">${text} ↗</a>`
    : text;
}

function benchlmSortValue(record, field) {
  if (field === "model_name" || field === "provider") return record[field];
  if (field === "benchlm_agentic") return record.agentic_score;
  if (field === "benchlm_overall") return record.overall_score;
  return record.benchmarks?.[field]?.score ?? null;
}

function benchlmSortHeader(field, label) {
  const active = state.benchlmSort === field;
  const direction = active ? state.benchlmDirection : null;
  const marker = active ? (direction === "asc" ? " ↑" : " ↓") : " ↕";
  const ariaSort = active ? (direction === "asc" ? "ascending" : "descending") : "none";
  return `<th aria-sort="${ariaSort}"><button data-benchlm-sort="${field}" title="Sort by ${escapeHtml(label)}">${escapeHtml(label)}${marker}</button></th>`;
}

function scoreRangeLabel(range, fallback) {
  if (!range || !Number.isFinite(range.min) || !Number.isFinite(range.max)) {
    return Number.isFinite(fallback) ? Number(fallback).toFixed(1) : "—";
  }
  return range.min === range.max ? Number(range.max).toFixed(1) : `${Number(range.min).toFixed(1)}–${Number(range.max).toFixed(1)}`;
}

function scoreRangeMax(range, fallback) {
  return range && Number.isFinite(range.max) ? Number(range.max) : fallback;
}

function representativePortfolioRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = `${row.model_id}::${row.agent_id || "model-level"}`;
    const current = groups.get(key);
    const quality = portfolioQuality(row).score;
    const currentQuality = current ? portfolioQuality(current).score : null;
    if (!current || (quality !== null && (currentQuality === null || quality > currentQuality))
      || (quality === currentQuality && row.configuration_id < current.configuration_id)) {
      groups.set(key, row);
    }
  });
  return [...groups.values()];
}

function portfolioQuality(row) {
  const overall = benchlmMetricValue(row, "benchlm_overall");
  if (overall !== null) return { score: overall, source: "BenchLM overall score" };
  const agentic = benchlmMetricValue(row, "benchlm_agentic");
  if (agentic !== null) return { score: agentic, source: "BenchLM agentic score" };
  const range = row.daily_driver_score_range;
  const score = range?.max ?? row.daily_driver_score;
  return Number.isFinite(score) ? { score, source: "observed Daily Driver range" } : { score: null, source: "" };
}

function portfolioTier(row) {
  if (!Number.isInteger(row.cost_tier)) return null;
  return row.cost_tier >= 4 ? "premium" : row.cost_tier >= 2 ? "balanced" : "value";
}

function portfolioOptionSortKey(candidate, targetTier) {
  const tierDistance = Math.abs(PORTFOLIO_TIER_ORDER[candidate.tier] - PORTFOLIO_TIER_ORDER[targetTier]);
  return [tierDistance, -candidate.quality.score, candidate.cost, candidate.row.configuration_id];
}

function comparePortfolioOptions(left, right, targetTier) {
  const leftKey = portfolioOptionSortKey(left, targetTier);
  const rightKey = portfolioOptionSortKey(right, targetTier);
  for (let index = 0; index < leftKey.length; index += 1) {
    if (leftKey[index] < rightKey[index]) return -1;
    if (leftKey[index] > rightKey[index]) return 1;
  }
  return 0;
}

function portfolioRecommendations(rows) {
  const budget = (state.view || DEFAULT_VIEW).monthly_budget_usd;
  const candidates = representativePortfolioRows(rows).map((row) => {
    const cost = monthlyCost(row);
    const quality = portfolioQuality(row);
    return { row, cost, tier: portfolioTier(row), quality };
  }).filter((candidate) => candidate.cost !== null && candidate.tier && candidate.quality.score !== null);
  if (!candidates.length) return null;
  const all = candidates;
  const pools = PORTFOLIO_ALLOCATIONS.map((allocation) => {
    const matching = candidates.filter((candidate) => candidate.tier === allocation.tier);
    return matching.length ? matching : all;
  });
  const choose = (allowReuse) => {
    let best = null;
    pools[0].forEach((specialist) => pools[1].forEach((balanced) => pools[2].forEach((volume) => {
      const selected = [specialist, balanced, volume];
      const identifiers = selected.map((candidate) => candidate.row.configuration_id);
      if (!allowReuse && new Set(identifiers).size < identifiers.length && candidates.length >= selected.length) return;
      const totalCost = selected.reduce((sum, candidate, index) => sum + PORTFOLIO_ALLOCATIONS[index].share * candidate.cost, 0);
      if (budget < BUDGET_UNLIMITED && totalCost > budget) return;
      const weightedQuality = selected.reduce((sum, candidate, index) => sum + PORTFOLIO_ALLOCATIONS[index].share * candidate.quality.score, 0);
      const distinct = new Set(identifiers).size;
      const ranking = [weightedQuality, -totalCost, distinct, identifiers.join("|")];
      if (!best || ranking[0] > best.ranking[0] || (ranking[0] === best.ranking[0] && (ranking[1] > best.ranking[1]
        || (ranking[1] === best.ranking[1] && (ranking[2] > best.ranking[2]
          || (ranking[2] === best.ranking[2] && ranking[3] > best.ranking[3])))))) {
        best = { selected, totalCost, ranking };
      }
    })));
    return best;
  };
  const best = choose(false) || choose(true);
  if (!best) return null;
  const reusedModel = new Set(best.selected.map((candidate) => candidate.row.configuration_id)).size < best.selected.length;
  return {
    budget,
    totalCost: best.totalCost,
    remaining: budget >= BUDGET_UNLIMITED ? null : budget - best.totalCost,
    reusedModel,
    allocations: best.selected.map((candidate, index) => {
      const allocation = PORTFOLIO_ALLOCATIONS[index];
      let optionPool = pools[index].slice().sort((left, right) => comparePortfolioOptions(left, right, allocation.tier));
      if (optionPool.length < PORTFOLIO_OPTION_COUNT) {
        const nearby = candidates
          .filter((option) => !optionPool.some((existing) => existing.row.configuration_id === option.row.configuration_id))
          .sort((left, right) => comparePortfolioOptions(left, right, allocation.tier));
        optionPool = optionPool.concat(nearby.slice(0, PORTFOLIO_OPTION_COUNT - optionPool.length));
      }
      const selectedId = candidate.row.configuration_id;
      optionPool = [candidate, ...optionPool.filter((option) => option.row.configuration_id !== selectedId)]
        .slice(0, PORTFOLIO_OPTION_COUNT);
      const options = optionPool.map((option) => {
        const mixCost = best.selected.reduce((sum, other, otherIndex) => sum + PORTFOLIO_ALLOCATIONS[otherIndex].share * (otherIndex === index ? option.cost : other.cost), 0);
        return {
          ...option,
          allocatedCost: option.cost * allocation.share,
          fitsBudget: budget >= BUDGET_UNLIMITED || mixCost <= budget,
          mixCost,
          selected: option.row.configuration_id === selectedId
        };
      });
      return {
        ...allocation,
        share_percent: Math.round(allocation.share * 100),
        ...candidate,
        allocatedCost: candidate.cost * allocation.share,
        options
      };
    })
  };
}

function withinBudget(row) {
  const budget = (state.view || DEFAULT_VIEW).monthly_budget_usd;
  if (budget === BUDGET_UNLIMITED) return true;
  const cost = monthlyCost(row);
  return cost !== null && cost <= budget;
}

function formatDollars(value) {
  if (value > 0 && value < 0.01) return "<$0.01";
  return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2, minimumFractionDigits: 0 });
}

function pricingProviderSlug(provider) {
  return String(provider || "unknown-provider").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "unknown-provider";
}

function pricingAnchor(rowOrProvider) {
  const provider = typeof rowOrProvider === "string" ? rowOrProvider : rowOrProvider?.provider;
  return `pricing.html#pricing-${pricingProviderSlug(provider)}`;
}

function pricingLink(rowOrProvider, text) {
  return `<a class="pricing-link" href="${pricingAnchor(rowOrProvider)}">${escapeHtml(text)}</a>`;
}

function monthlyEstimateLabel(row) {
  const cost = monthlyCost(row);
  return cost === null ? "Monthly estimate unavailable" : `Est. ${formatDollars(cost)}/month`;
}

function recommendationCostLabel(row, label) {
  const estimate = monthlyEstimateLabel(row);
  return estimate;
}

function syncBudgetAmount() {
  document.querySelector("#monthly-budget-amount").value = state.view.monthly_budget_usd;
  document.querySelector("#monthly-budget-amount").setAttribute("aria-invalid", "false");
  document.querySelector("#budget-amount-error").textContent = "";
}

function updateBudgetAmount() {
  const input = document.querySelector("#monthly-budget-amount");
  const value = Number(input.value);
  if (!input.value.trim() || !Number.isInteger(value) || value < 0 || value > BUDGET_UNLIMITED) {
    input.setAttribute("aria-invalid", "true");
    document.querySelector("#budget-amount-error").textContent = "Enter whole dollars from 0 to 5,000. The last valid budget is still applied.";
    return;
  }
  document.querySelector("#monthly-budget").value = value;
  syncViewFromControls();
  saveView();
  render();
}

function monthlyCalculation(row) {
  const cost = monthlyCost(row);
  if (cost === null) return "";
  const view = state.view || DEFAULT_VIEW;
  const inputMillions = view.monthly_input_tokens / 1000000;
  const outputMillions = view.monthly_output_tokens / 1000000;
  const formula = `${inputMillions.toLocaleString("en-US", {maximumFractionDigits: 6})}M input × ${formatDollars(row.input_price_per_million_usd)}/1M + ${outputMillions.toLocaleString("en-US", {maximumFractionDigits: 6})}M output × ${formatDollars(row.output_price_per_million_usd)}/1M = ${formatDollars(cost)}/month`;
  const source = row.pricing_source_url ? `<a href="${safeHref(row.pricing_source_url)}" target="_blank" rel="noreferrer">Snapshot token prices ↗</a>` : "Snapshot token prices";
  return `<details class="cost-calculation"><summary>Cost calculation</summary><p>${pricingLink(row, formula)}</p><p>Assumed API usage, not a subscription price or measured task cost. ${source}</p></details>`;
}

function bestMonthlyValue(rows, scoreFor) {
  return rows.filter((row) => monthlyCost(row) !== null).reduce((best, row) => {
    const value = monthlyCost(row) / Math.max(scoreFor(row), 0.001);
    const bestValue = best ? monthlyCost(best) / Math.max(scoreFor(best), 0.001) : Infinity;
    return !best || value < bestValue || (value === bestValue && (scoreFor(row) > scoreFor(best)
      || (scoreFor(row) === scoreFor(best) && row.model_name < best.model_name))) ? row : best;
  }, null);
}

function updateUsageAssumptions() {
  const input = document.querySelector("#monthly-input-million");
  const output = document.querySelector("#monthly-output-million");
  if (!input.value || !output.value || !input.checkValidity() || !output.checkValidity()) {
    document.querySelector("#budget-error").textContent = "Enter 0–1,000 million tokens. The last valid estimate is still shown.";
    return;
  }
  state.view.monthly_input_tokens = Math.round(Number(input.value) * 1000000);
  state.view.monthly_output_tokens = Math.round(Number(output.value) * 1000000);
  document.querySelector("#budget-error").textContent = "";
  saveView();
  render();
}

function recommendationRows(rows) {
  rows = rows.filter(withinBudget);
  if (!rows.length) return [];
  const isDailyDriver = rows.some((row) => row.category === DAILY_DRIVER_CATEGORY);
  const eligibleRows = isDailyDriver
    ? rows.filter((row) => Number(row.coverage || 0) >= DAILY_DRIVER_MIN_COVERAGE)
    : rows;
  const rankedRows = eligibleRows.length ? eligibleRows : rows;
  const scoreFor = (row) => scoreRangeMax(row.daily_driver_score_range, row.score);
  const quality = rankedRows.reduce((best, row) => !best || scoreFor(row) > scoreFor(best) || (scoreFor(row) === scoreFor(best) && row.model_name < best.model_name) ? row : best, null);
  const recommendations = [["best_quality", quality]];
  const value = bestMonthlyValue(rankedRows, scoreFor);
  if (value) recommendations.push(["best_value", value]);
  return recommendations;
}

function recommendationText(label, row) {
  const coverage = `${row.coverage}/${row.coverage_total} work categories`;
  return recommendationBlock(label, row, scoreRangeLabel(row.daily_driver_score_range, row.score), coverage, recommendationCostLabel(row, label), "", row.score_basis || row.daily_driver_score_basis);
}

function modelBadge(row) {
  const identity = `${row.model_id || ""} ${row.configuration_label || ""} ${row.model_name || ""}`.toLowerCase();
  const family = identity.includes("claude") ? ["claude", "C"]
    : identity.includes("gemini") ? ["gemini", "G"]
      : identity.includes("grok") ? ["grok", "X"]
      : identity.includes("composer") ? ["composer", "Co"]
          : identity.includes("gpt") ? ["gpt", "O"]
            : ["generic", "AI"];
  return `<span class="model-badge model-badge-${family[0]}" aria-hidden="true">${family[1]}</span>`;
}

function modelLink(row) {
  const name = escapeHtml(row.configuration_label || row.model_name);
  const content = `${modelBadge(row)}${name}`;
  return row.profile_url ? `<a class="model-link" href="${safeHref(row.profile_url)}" target="_blank" rel="noreferrer">${content} ↗</a>` : content;
}

function recommendationBlock(label, row, score, coverage, cost, evidence, scoreBasis = "") {
  const labelText = label === "best_quality" ? (row.category === DAILY_DRIVER_CATEGORY ? "Best Daily Driver Fit" : "Best Quality") : "Best Value";
  const labelClass = label === "best_quality" ? "quality" : "value";
  const costIsOverBudget = label === "best_quality" && monthlyCost(row) !== null && !withinBudget(row);
  const costLabel = cost ? `<span class="${costIsOverBudget ? "recommendation-cost-over-budget" : ""}">${cost === "Monthly estimate unavailable" ? escapeHtml(cost) : pricingLink(row, cost)}</span>` : "";
  const evidenceLinks = evidence ? `<div class="recommendation-evidence">${evidence}</div>` : "";
  const displayScore = typeof score === "number" ? score.toFixed(1) : escapeHtml(score);
  const scoreLabel = String(scoreBasis || "").startsWith("BenchLM")
    ? scoreBasis
    : "modelagency derived · observed range";
  const scoreValue = displayScore === "—" ? displayScore : `${displayScore}/100`;
  return `<div class="recommendation-item recommendation-${labelClass}"><div class="recommendation-label">${labelText}</div><div class="recommendation-main"><div class="recommendation-model">${modelLink(row)}</div></div><div class="recommendation-meta"><span>${escapeHtml(coverage)}</span>${costLabel}</div><div class="recommendation-footer"><div class="recommendation-score"><strong>${scoreValue}</strong><span>${escapeHtml(scoreLabel)}</span></div><div class="recommendation-footer-row"><div class="recommendation-cost-calculation">${monthlyCalculation(row)}</div><div class="recommendation-supporting">${evidenceLinks}</div></div></div></div>`;
}

function recommendationCard(category, rows, extraClass = "", includeHeading = true) {
  const lines = recommendationRows(rows).map(([label, row]) => recommendationText(label, row)).join("");
  if (!lines) return "";
  const heading = includeHeading ? `<h3>${escapeHtml(formatLabel(category))}</h3>` : "";
  const description = DOMAIN_DESCRIPTIONS[category]
    ? `<p class="category-description">${escapeHtml(DOMAIN_DESCRIPTIONS[category])}</p>`
    : "";
  return `<article class="card ${extraClass}">${heading}${description}<div class="recommendation-list">${lines}</div></article>`;
}

function domainRecommendationRows(rows, domain) {
  const domainRows = rows.filter((row) => row.domain_scores?.[domain] !== undefined && row.domain_scores?.[domain] !== null);
  const affordableRows = domainRows.filter(withinBudget);
  if (!affordableRows.length) return [];
  const scoreFor = (row) => scoreRangeMax(row.domain_score_ranges?.[domain], row.domain_scores[domain]);
  const quality = domainRows.reduce((best, row) => {
    const score = scoreFor(row);
    const bestScore = best ? scoreFor(best) : null;
    return !best || score > bestScore || (score === bestScore && row.model_name < best.model_name) ? row : best;
  }, null);
  const recommendations = [["best_quality", quality]];
  const value = bestMonthlyValue(affordableRows, scoreFor);
  if (value) recommendations.push(["best_value", value]);
  return recommendations;
}

function domainEvidenceLinks(row, domain) {
  const categories = new Set(DOMAIN_CATEGORIES[domain] || []);
  const entries = row.evidence.filter((entry) => categories.has(entry.category));
  return entries.map((entry) => `<a href="${safeHref(entry.evidence_url)}" target="_blank" rel="noreferrer">${escapeHtml(entry.benchmark_id)} ↗</a>`).join(" · ");
}

function domainRecommendationText(label, row, domain) {
  return recommendationBlock(label, row, scoreRangeLabel(row.domain_score_ranges?.[domain], row.domain_scores[domain]),
    `${row.domain_coverage[domain]}/${row.domain_coverage_total[domain]} subcategories`,
    recommendationCostLabel(row, label), domainEvidenceLinks(row, domain), row.domain_score_bases?.[domain] || row.score_basis);
}

function domainRecommendationCard(domain, rows) {
  const lines = domainRecommendationRows(rows, domain)
    .map(([label, row]) => domainRecommendationText(label, row, domain))
    .join("");
  if (!lines) return "";
  const heading = `<h3>${escapeHtml(formatLabel(domain))}</h3>`;
  const description = DOMAIN_DESCRIPTIONS[domain]
    ? `<p class="category-description">${escapeHtml(DOMAIN_DESCRIPTIONS[domain])}</p>`
    : "";
  return `<article class="card">${heading}${description}<div class="recommendation-list">${lines}</div></article>`;
}

function portfolioCard(rows) {
  const recommendation = portfolioRecommendations(rows);
  if (!recommendation) {
    if (!rows.length) return "";
    const message = rows.some(withinBudget)
      ? "No three-tier mix fits this budget and expected usage. Reduce usage, raise the budget, or select a lower-cost model."
      : "No priced models fit this budget at full workload. Reduce expected usage, raise the budget, or select a lower-cost model.";
    return `<article class="card portfolio-card"><div class="section-heading"><h3>Recommended workload mix</h3><span class="pill">Budget not met</span></div><p class="category-description">${message}</p></article>`;
  }
  const remaining = recommendation.remaining === null ? "no cap" : `${formatDollars(recommendation.remaining)} remaining`;
  const allocations = recommendation.allocations.map((allocation) => {
    const options = (allocation.options || [{
      row: allocation.row,
      cost: allocation.cost,
      quality: allocation.quality,
      selected: true,
      fitsBudget: true,
      allocatedCost: allocation.allocatedCost
    }]).map((option) => {
      const score = formatMetric(option.quality.score);
      const fullCost = formatDollars(option.cost);
      const allocatedCost = formatDollars(option.allocatedCost);
      const source = option.quality.source;
      const budgetNote = option.fitsBudget ? "" : `<span class="portfolio-option-budget-warning"> · Over budget</span>`;
      const optionLabel = option.selected ? "Selected fit" : "Alternative";
      return `<div class="portfolio-option${option.selected ? " portfolio-option-selected" : ""}"><div class="portfolio-option-header"><span>${optionLabel}</span><strong>${score}</strong></div><div class="portfolio-option-model">${modelLink(option.row)}</div><small>${escapeHtml(source)} · ${pricingLink(option.row, `${allocatedCost}/mo share`)} (${pricingLink(option.row, `${fullCost} full workload`)})${budgetNote}</small></div>`;
    }).join("");
    return `<div class="portfolio-allocation portfolio-${escapeHtml(allocation.key)}"><div class="portfolio-allocation-header"><span class="portfolio-share">${allocation.share_percent}%</span><strong class="portfolio-allocation-title">${escapeHtml(allocation.label)}</strong></div><div class="portfolio-options" aria-label="${escapeHtml(allocation.label)} options">${options}</div></div>`;
  }).join("");
  const reuseNote = recommendation.reusedModel
    ? " No distinct three-tier mix fits this budget and usage, so the most efficient selected model is reused."
    : "";
  return `<article class="card portfolio-card"><div class="section-heading portfolio-heading"><h3>Recommended workload mix</h3><div class="portfolio-header-meta"><span class="portfolio-total">Estimated allocation: <strong><a class="pricing-link" href="pricing.html#pricing-overview">${formatDollars(recommendation.totalCost)}/month</a></strong> · ${remaining}</span></div></div><p class="category-description">Source scores drive each tier: a high-end model for targeted work, a balanced model for everyday tasks, and an economical model for volume. Each tier shows the selected budget fit plus a score-ranked alternative when available. Shares describe workload, not a promise to spend that percentage of the budget.${reuseNote}</p><div class="portfolio-grid">${allocations}</div></article>`;
}

function renderRecommendations() {
  const container = document.querySelector("#suggestions");
  const selected = filteredSummaryRows();
  const affordable = selected.filter(withinBudget);
  const modelCount = selectedModelCount();
  const budget = (state.view || DEFAULT_VIEW).monthly_budget_usd;
  const unlimited = budget === BUDGET_UNLIMITED;
  const budgetLabel = unlimited ? "$5,000+" : formatDollars(budget);
  document.querySelector("#monthly-budget-amount").value = budget;
  document.querySelector("#monthly-budget").setAttribute("aria-valuetext", unlimited ? "$5,000 or more; no budget cap" : `${budgetLabel} per month`);
  const unknown = selected.filter((row) => monthlyCost(row) === null).length;
  const unknownNote = unknown ? ` ${unknown} without token prices${unlimited ? "." : "; excluded from budget recommendations."}` : "";
  document.querySelector("#budget-status").textContent = unlimited
    ? `No budget cap · estimates use your monthly token workload.${unknownNote}`
    : `${affordable.length} of ${modelCount} selected models fit ${budgetLabel}/month at full workload with your usage assumptions.${unknownNote}`;
  const regularCards = DOMAIN_COLUMNS.map(([domain]) => domainRecommendationCard(domain, filteredSummaryRows())).filter(Boolean);
  const dailyRows = recommendationSourceRows().filter((row) => row.category === DAILY_DRIVER_CATEGORY);
  const dailyCard = dailyRows.length
    ? recommendationCard(DAILY_DRIVER_CATEGORY, dailyRows, "daily-driver-card")
    : "";
  const report = [];
  const portfolio = portfolioCard(selected);
  if (portfolio) report.push(portfolio);
  const categoryCards = [...regularCards, dailyCard].filter(Boolean);
  if (categoryCards.length) report.push(`<div class="recommendation-grid">${categoryCards.join("")}</div>`);
  container.innerHTML = report.join("") || (selected.length && !affordable.length
    ? '<p class="muted">No priced models fit this budget. Increase the budget or adjust the usage assumptions.</p>'
    : '<p class="muted">No recommendations match the current view.</p>');
}

function recommendationSourceRows() {
  const search = document.querySelector("#search").value.trim().toLowerCase();
  const models = selectedValues("model-filters");
  const agents = selectedAgentValues();
  return state.records.filter((row) => {
    const text = [row.configuration_label, row.model_name, row.configuration_id, row.model_id, row.effort_level, row.provider, row.category, row.benchmark_id].join(" ").toLowerCase();
    return (!search || text.includes(search)) &&
      models.has(modelFilterId(row)) && agents.has(agentLabel(row));
  });
}

function summarySortValue(row) {
  if (state.sort === "monthly_cost") return monthlyCost(row);
  if (BENCHLM_METRIC_FIELDS.some(([key]) => key === state.sort)) return benchlmMetricValue(row, state.sort);
  if (state.sort === "daily_driver") return scoreRangeMax(row.daily_driver_score_range, row.daily_driver_score);
  if (DOMAIN_COLUMNS.some(([key]) => key === state.sort)) return scoreRangeMax(row.domain_score_ranges?.[state.sort], row.domain_scores[state.sort]);
  if (state.sort === "cost_tier") return row.cost_tier;
  return row[state.sort];
}

function filteredSummaryRows() {
  const search = document.querySelector("#search").value.trim().toLowerCase();
  const models = selectedValues("model-filters");
  const agents = selectedAgentValues();
  return state.summaries.filter((row) => {
    const text = [row.configuration_label, row.model_name, row.configuration_id, row.model_id, row.effort_level, row.provider, ...Object.keys(row.category_scores), ...Object.keys(row.domain_scores)].join(" ").toLowerCase();
    return (!search || text.includes(search)) && models.has(modelFilterId(row));
  }).filter((row) => agents.has(agentLabel(row)));
}

function rosterOnlyComparisonRows() {
  const search = document.querySelector("#search").value.trim().toLowerCase();
  const models = selectedValues("model-filters");
  const summarizedModels = new Set(state.summaries.map(modelFilterId));
  return [...models]
    .filter((modelId) => MODEL_ROSTER[modelId] && !summarizedModels.has(modelId))
    .map((modelId) => {
      const modelName = MODEL_ROSTER[modelId];
      const pricing = rosterPricingRecord(modelId);
      return {
        model_id: modelId,
        model_name: modelName,
        configuration_id: modelId,
        configuration_label: modelName,
        provider: MODEL_ROSTER_PROVIDERS[modelId] || "Unknown",
        category_scores: {},
        domain_scores: {},
        domain_score_ranges: {},
        domain_score_bases: {},
        domain_coverage: {},
        domain_coverage_total: {},
        coverage: 0,
        coverage_total: DAILY_DRIVER_CATEGORY_COUNT,
        daily_driver_score: null,
        daily_driver_score_range: null,
        daily_driver_score_basis: "No benchmark data in this snapshot",
        evidence: [],
        profile_url: pricing?.profile_url || null,
        input_price_per_million_usd: pricing?.input_price_per_million_usd ?? null,
        output_price_per_million_usd: pricing?.output_price_per_million_usd ?? null,
        pricing_source_url: pricing?.pricing_source_url || null,
        pricing_variant: pricing?.pricing_variant || null,
        pricing_notes: pricing?.notes || null,
        roster_only: true
      };
    })
    .filter((row) => !search || [row.model_name, row.model_id, row.provider].join(" ").toLowerCase().includes(search));
}

function visibleRows() {
  return [...filteredSummaryRows(), ...rosterOnlyComparisonRows()].sort((left, right) => {
    const a = summarySortValue(left);
    const b = summarySortValue(right);
    if (a === b) return left.model_name.localeCompare(right.model_name);
    if (a === null || a === undefined) return 1;
    if (b === null || b === undefined) return -1;
    const result = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b));
    return state.direction === "asc" ? result : -result;
  });
}

function renderEvidenceLinks(row) {
  const links = row.evidence.map((entry) => {
    const benchmark = `<a href="${safeHref(entry.evidence_url)}" target="_blank" rel="noreferrer" title="${escapeHtml(entry.attribution)}">${escapeHtml(entry.benchmark_id)} ↗</a>`;
    return `<span class="evidence-item">${benchmark}</span>`;
  }).join(" · ");
  return `<div class="evidence-links">${links}</div>`;
}

function renderEvidenceDetails(row) {
  const details = row.evidence.map((entry) => {
    const original = entry.original_source_url
      ? ` <a href="${safeHref(entry.original_source_url)}" target="_blank" rel="noreferrer">original ↗</a>`
      : "";
    const license = entry.source_license_url ? ` · <a href="${safeHref(entry.source_license_url)}" target="_blank" rel="noreferrer">license / terms</a>` : "";
    return `<li><strong>${escapeHtml(formatLabel(entry.category))} · ${escapeHtml(entry.benchmark_id)}</strong>: ${escapeHtml(entry.score)} ${escapeHtml(entry.score_unit)}; ${escapeHtml(entry.attribution)}${original}<br><small>Retrieved ${escapeHtml(entry.retrieved_date || "unavailable")} · ${escapeHtml(entry.source_status || "unavailable")}${license}</small></li>`;
  }).join("");
  return `<div class="evidence-expanded">${renderEvidenceLinks(row)}<ul>${details}</ul></div>`;
}

function renderSummaryEvidence(row, index) {
  if (row.roster_only) return "<small class=\"muted\">No snapshot benchmark data</small>";
  return `<small>${row.evidence.length} benchmark${row.evidence.length === 1 ? "" : "s"}</small><details class="evidence-toggle" data-evidence-row="${index}" aria-controls="evidence-row-${index}"><summary>attribution / credit</summary></details>`;
}

function renderBenchLMMetrics() {
  const container = document.querySelector("#benchlm-metrics");
  const available = state.benchlmMetrics.status === "available";
  if (!available) {
    container.innerHTML = '<p class="canonical-empty">BenchLM source metrics are unavailable in this snapshot. Follow the source link to inspect the live leaderboard.</p>';
    return;
  }
  const models = selectedValues("model-filters");
  const modelCount = models.size;
  const search = document.querySelector("#search").value.trim().toLowerCase();
  const selectedRecords = state.benchlmMetrics.records.filter((record) => {
    const modelSelected = models.has(record.model_id);
    return modelSelected;
  });
  const metricModelIds = new Set(state.benchlmMetrics.records.map((record) => record.model_id));
  const missingModelLabels = [...models]
    .filter((modelId) => !metricModelIds.has(modelId))
    .map((modelId) => modelDisplayName(modelId));
  const missingNote = missingModelLabels.length
    ? ` · No BenchLM metrics published for ${missingModelLabels.map((label) => escapeHtml(label)).join(", ")}`
    : "";
  const records = selectedRecords.filter((record) => {
    return !search || [record.model_name, record.model_id, record.provider].join(" ").toLowerCase().includes(search);
  }).sort((left, right) => {
    const leftValue = benchlmSortValue(left, state.benchlmSort);
    const rightValue = benchlmSortValue(right, state.benchlmSort);
    if (leftValue === rightValue) return left.model_name.localeCompare(right.model_name);
    if (leftValue === null || leftValue === undefined) return 1;
    if (rightValue === null || rightValue === undefined) return -1;
    const result = typeof leftValue === "number" && typeof rightValue === "number"
      ? leftValue - rightValue
      : String(leftValue).localeCompare(String(rightValue));
    return state.benchlmDirection === "asc" ? result : -result;
  });
  const body = records.map((record) => {
    const overall = record.overall_score === null ? "—" : `${formatMetric(record.overall_score, 2)}<small>#${escapeHtml(record.overall_rank ?? "—")} ${escapeHtml(record.overall_status || "")}</small>`;
    const agentic = record.agentic_score === null ? "—" : `${formatMetric(record.agentic_score)}<small>#${escapeHtml(record.agentic_rank ?? "—")}</small>`;
    const row = { model_id: record.model_id };
    return `<tr><td>${modelLink(record)}<br><small>${escapeHtml(record.provider)}</small></td><td class="score-cell">${agentic}</td><td class="score-cell">${metricCell(row, "terminal_bench_2")}</td><td class="score-cell">${metricCell(row, "browsecomp")}</td><td class="score-cell">${metricCell(row, "osworld_verified")}</td><td class="score-cell">${overall}</td></tr>`;
  }).join("");
  const date = escapeHtml(state.benchlmMetrics.retrieved_date || "unavailable");
  const searchNote = search && records.length !== selectedRecords.length ? ` · ${records.length} match search` : "";
  container.innerHTML = `<p class="muted">${selectedRecords.length} of ${modelCount} selected models have BenchLM metrics${missingNote}${searchNote} · source values retrieved ${date}. Missing cells mean BenchLM does not publish that exact benchmark value for the model.</p><div class="table-wrap"><table class="canonical-table benchlm-metrics-table"><thead><tr>${benchlmSortHeader("model_name", "Model")}${benchlmSortHeader("benchlm_agentic", "Agentic score")}${benchlmSortHeader("terminal_bench_2", "Terminal-Bench 2.0")}${benchlmSortHeader("browsecomp", "BrowseComp")}${benchlmSortHeader("osworld_verified", "OSWorld-Verified")}${benchlmSortHeader("benchlm_overall", "Overall")}</tr></thead><tbody>${body}</tbody></table></div>`;
  container.querySelectorAll("[data-benchlm-sort]").forEach((button) => button.addEventListener("click", () => {
    const sort = button.dataset.benchlmSort;
    state.benchlmDirection = state.benchlmSort === sort && state.benchlmDirection === "desc" ? "asc" : "desc";
    state.benchlmSort = sort;
    renderBenchLMMetrics();
  }));
}

function renderCanonical() {
  const container = document.querySelector("#canonical-results");
  const available = state.leaderboard.status === "available";
  document.querySelector("#ranking-lane-control").hidden = !available;
  if (!available) {
    container.innerHTML = '<p class="canonical-empty">Published ranks and verification lanes are not available in this snapshot. Follow the source link to see BenchLM’s leaderboard.</p>';
    return;
  }
  const models = selectedValues("model-filters");
  const search = document.querySelector("#search").value.trim().toLowerCase();
  const lane = document.querySelector("#ranking-lane").value;
  const rows = state.leaderboard.records.filter((row) =>
    models.has(row.configuration_id) && row.lane === lane
    && (!search || [row.model_name, row.model_id, row.configuration_id].join(" ").toLowerCase().includes(search)));
  const date = escapeHtml(state.leaderboard.retrieved_date);
  const body = rows.map((row) => `<tr><td>${modelLink(row)}</td><td>${escapeHtml(row.source_rank ?? "—")}</td><td>${escapeHtml(row.source_score ?? "—")}</td><td>${escapeHtml(row.evidence_status)}</td></tr>`).join("");
  container.innerHTML = `<p class="muted">${rows.length} models · ${escapeHtml(lane)} lane · retrieved ${date}</p><div class="table-wrap"><table class="canonical-table"><thead><tr><th>Model</th><th>Published rank</th><th>Published score</th><th>Evidence status</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function pricingCheckedDate() {
  const dates = [...state.records.map((row) => row.retrieved_date), ...(state.rosterPricing.records || []).map((row) => row.retrieved_date), state.rosterPricing.retrieved_date, state.sourceContext.retrieved_date]
    .filter(Boolean)
    .sort();
  return dates.length ? dates[dates.length - 1] : "unavailable";
}

function renderPricingNotes() {
  const container = document.querySelector("#pricing-section");
  if (!container) return;
  const checkedDate = escapeHtml(pricingCheckedDate());
  const sources = [...new Set([
    ...state.summaries.map((row) => row.pricing_source_url),
    ...(state.rosterPricing.records || []).map((row) => row.pricing_source_url)
  ].filter(Boolean))];
  const sourceLinks = sources.length
    ? sources.map((sourceUrl) => `<a href="${safeHref(sourceUrl)}" target="_blank" rel="noreferrer">${escapeHtml(sourceUrl)} ↗</a>`).join(" · ")
    : "Unavailable in this snapshot";
  container.innerHTML = `<p class="pricing-summary">Token prices used for estimates are snapshot input and output prices per 1M tokens. Primary pricing source(s), checked ${checkedDate}: ${sourceLinks}.</p><a class="note-backlink" href="pricing.html#pricing-overview">View full token pricing list ↗</a>`;
}

function render() {
  document.querySelector("#model-count").textContent = `${selectedModelCount()} selected`;
  const rows = visibleRows();
  const activeDomainKeys = new Set(
    rows.length
      ? DOMAIN_COLUMNS
        .filter(([key]) => rows.some((row) => row.domain_scores[key] !== undefined && row.domain_scores[key] !== null))
        .map(([key]) => key)
      : DOMAIN_COLUMNS.map(([key]) => key)
  );
  document.querySelectorAll("[data-domain-column]").forEach((cell) => {
    cell.hidden = !activeDomainKeys.has(cell.dataset.domainColumn);
  });
  document.querySelector("#status").textContent = `${rows.length} of ${comparisonModelCount()} models`;
  document.querySelector("#results").innerHTML = rows.map((row, index) => {
    const metricRecord = benchlmMetricRecord(row);
    const sourceMetricCells = BENCHLM_METRIC_FIELDS.map(([field]) => {
      const decimals = field === "benchlm_overall" ? 2 : 1;
      const rank = field === "benchlm_agentic" ? metricRecord?.agentic_rank : field === "benchlm_overall" ? metricRecord?.overall_rank : null;
      const status = field === "benchlm_overall" ? metricRecord?.overall_status : null;
      const meta = rank === null || rank === undefined ? "" : `<small>#${escapeHtml(rank)}${status ? ` · ${escapeHtml(status)}` : ""}</small>`;
      return `<td class="score-cell">${metricCell(row, field, decimals)}${meta}</td>`;
    }).join("");
    const domainCells = DOMAIN_COLUMNS.map(([key]) => {
      const score = row.domain_scores[key];
      const coverage = row.domain_coverage?.[key] !== undefined
        ? `${row.domain_coverage[key]}/${row.domain_coverage_total[key]} subcategories covered`
        : "No linked benchmark evidence";
      const hidden = activeDomainKeys.has(key) ? "" : " hidden";
      const range = row.domain_score_ranges?.[key];
      const rangeTitle = range && range.min !== range.max ? ` · ${escapeHtml(row.score_range_basis || "observed configurations")}` : "";
      const basis = row.domain_score_bases?.[key] || "modelagency derived percentile index";
      return `<td data-domain-column="${key}"${hidden} class="score-cell" title="${escapeHtml(coverage)} · ${escapeHtml(basis)}${rangeTitle}">${score === undefined ? "—" : `${escapeHtml(scoreRangeLabel(range, score))}<small>${row.domain_coverage[key]}/${row.domain_coverage_total[key]} covered</small>`}</td>`;
    }).join("");
    const dailyDriver = escapeHtml(scoreRangeLabel(row.daily_driver_score_range, row.daily_driver_score));
    const cost = monthlyCost(row);
    const budgetLabel = cost === null ? "Price unavailable" : (state.view || DEFAULT_VIEW).monthly_budget_usd === BUDGET_UNLIMITED
      ? "No budget cap" : withinBudget(row) ? "Within budget" : "Over budget";
    return `<tr>
      <td class="model-cell">${modelLink(row)}<small class="model-provider">${escapeHtml(row.provider)} (${escapeHtml(row.configuration_id || row.model_id)})</small></td>
      <td>${escapeHtml(row.provider)}</td>
      ${sourceMetricCells}
      ${domainCells}
      <td class="score-cell" title="${escapeHtml(row.daily_driver_score_basis || "modelagency derived percentile + coverage")}">${dailyDriver}<small>${row.coverage}/${row.coverage_total} covered</small></td>
      <td class="monthly-cost ${cost !== null && !withinBudget(row) ? "over-budget" : ""}">${cost === null ? "—" : pricingLink(row, formatDollars(cost))}<small>${budgetLabel}</small></td>
      <td class="attribution">${renderSummaryEvidence(row, index)}</td>
    </tr><tr id="evidence-row-${index}" class="comparison-evidence-row" hidden><td colspan="13">${renderEvidenceDetails(row)}</td></tr>`;
  }).join("");
  document.querySelectorAll("#results .evidence-toggle").forEach((toggle) => toggle.addEventListener("toggle", () => {
    const evidenceRow = document.querySelector(`#evidence-row-${toggle.dataset.evidenceRow}`);
    if (evidenceRow) evidenceRow.hidden = !toggle.open;
  }));
  renderRecommendations();
  renderBenchLMMetrics();
  renderCanonical();
  renderPricingNotes();
}

function initialize(payload) {
  state.records = payload.records || [];
  state.summaries = payload.model_summaries || [];
  state.sourceContext = payload.source_context || {};
  state.leaderboard = payload.benchlm_leaderboard || { status: "unavailable", records: [] };
  state.benchlmMetrics = payload.benchlm_metrics || { status: "unavailable", records: [] };
  state.rosterPricing = payload.roster_pricing || { status: "unavailable", records: [] };
  document.querySelector("#source-attribution").textContent = state.sourceContext.attribution || "Benchmark data from BenchLM.ai; retrieval date unavailable.";
  document.querySelector("#snapshot-status").textContent = `${state.summaries.length} models · ${state.records.filter((row) => row.derivation_type !== "derived").length} benchmark results · Retrieved ${state.sourceContext.retrieved_date || "unavailable"}`;
  state.defaultView = canonicalizeView(payload.default_view || DEFAULT_VIEW);
  state.view = canonicalizeView(readStoredView(state.defaultView));
  state.sort = state.view.sort;
  state.direction = state.view.direction;
  makeFilter("model-filters", filterValues("model_id"), state.view.models, modelDisplayName);
  applyViewToControls();
  syncViewFromControls();
  saveView();
  render();
}

document.querySelector("#apply-yaml").addEventListener("click", applyYaml);
document.querySelector("#export-yaml").addEventListener("click", exportYaml);
document.querySelector("#reset-view").addEventListener("click", () => {
  state.view = normalizeView(state.defaultView);
  applyViewToControls();
  saveView();
  render();
  setViewStatus("Demo defaults restored.");
});
document.querySelectorAll("[data-filter-action]").forEach((button) => button.addEventListener("click", () => {
  setAllFilters(button.dataset.filterTarget, button.dataset.filterAction === "all");
}));
document.querySelectorAll("[data-sort]").forEach((button) => button.addEventListener("click", () => {
  const sort = button.dataset.sort;
  state.direction = state.sort === sort && state.direction === "desc" ? "asc" : "desc";
  state.sort = sort;
  syncViewFromControls();
  saveView();
  render();
}));
document.querySelector("#search").addEventListener("input", () => { syncViewFromControls(); saveView(); render(); });
document.querySelector("#ranking-lane").addEventListener("change", renderCanonical);
document.querySelector("#monthly-budget").addEventListener("input", () => { syncViewFromControls(); saveView(); render(); });
document.querySelector("#monthly-budget-amount").addEventListener("input", updateBudgetAmount);
document.querySelector("#monthly-input-million").addEventListener("input", updateUsageAssumptions);
document.querySelector("#monthly-output-million").addEventListener("input", updateUsageAssumptions);

fetch("data/results.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(initialize)
  .catch((error) => {
    document.querySelector("#status").textContent = `Unable to load generated data: ${error}`;
  });
