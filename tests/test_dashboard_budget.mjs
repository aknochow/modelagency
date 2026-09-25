import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createContext, runInContext } from "node:vm";

const appSource = readFileSync(new URL("../site/app.js", import.meta.url), "utf8");
const fixture = JSON.parse(readFileSync(new URL("../site/data/results.json", import.meta.url), "utf8"));

function dashboard(savedView) {
  const elements = new Map();
  const storage = new Map([["modelagency-roster-gpt-6-astra-v1", "1"]]);
  if (savedView) storage.set("modelagency-view-v1", JSON.stringify(savedView));
  function element(selector) {
    if (!elements.has(selector)) {
      elements.set(selector, {
        _value: "", _html: "", checked: false, textContent: "", children: [], listeners: {}, attributes: {},
        classList: { toggle() {} },
        get value() { return this._value; },
        set value(value) { this._value = String(value); },
        get innerHTML() { return this._html; },
        set innerHTML(value) {
          this._html = value;
          if (selector === "#model-filters" || selector === "#agent-filters") {
            this.children = [...value.matchAll(/<input\b[^>]*>/g)].map(([tag]) => {
              const child = element(`#${tag.match(/id="([^"]+)"/)[1]}`);
              child.dataset = { filterValue: tag.match(/data-filter-value="([^"]+)"/)[1] };
              child.checked = /\schecked[\s>]/.test(tag);
              return child;
            });
          }
          if (selector === "#benchlm-metrics") {
            this.children = [...value.matchAll(/<button\b[^>]*data-benchlm-sort="([^"]+)"[^>]*>/g)].map(([, sort]) => ({
              dataset: { benchlmSort: sort },
              listeners: {},
              addEventListener(event, handler) { this.listeners[event] = handler; }
            }));
          }
        },
        addEventListener(event, handler) { this.listeners[event] = handler; },
        setAttribute(name, value) { this.attributes[name] = value; },
        querySelectorAll() { return this.children; },
        checkValidity() {
          const value = Number(this.value);
          return Number.isFinite(value) && value >= 0 && value <= 1000;
        }
      });
    }
    return elements.get(selector);
  }
  const context = createContext({
    payload: structuredClone(fixture),
    document: {
      querySelector: element,
      querySelectorAll(selector) {
        const match = selector.match(/^(#(?:model|agent)-filters) input(:checked)?$/);
        return match ? element(match[1]).children.filter(child => !match[2] || child.checked) : [];
      }
    },
    localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
    fetch: () => new Promise(() => {})
  });
  runInContext(appSource, context);
  runInContext("initialize(payload)", context);
  return {
    element, storage,
    evaluate: code => runInContext(code, context),
    setBudget(value) {
      element("#monthly-budget").value = value;
      element("#monthly-budget").listeners.input();
    }
  };
}

export function runBudgetTests() {
  const passed = [];
  function check(name, verify) {
    verify();
    passed.push(name);
  }

  check("defaults, plain editor, and attributed export", () => {
    const page = dashboard();
    assert.equal(page.element("#monthly-budget-amount").value, "300");
    assert.equal(page.element("#monthly-budget-amount").value, "300");
    assert.equal(page.element("#monthly-input-million").value, "20");
    assert.equal(page.element("#monthly-output-million").value, "5");
    assert.equal(page.evaluate("state.view.models.includes('composer-2-5')"), true);
    assert.equal(page.evaluate("state.view.models.includes('gemini-3-1-pro')"), true);
    assert.match(page.element("#model-filters").innerHTML, /Composer 2\.5 \(Cursor\)/);
    assert.match(page.element("#model-filters").innerHTML, /Gemini 3\.1 Pro \(gemini-3-1-pro\)/);
    assert.equal(page.element("#model-count").textContent, "11 selected");
    assert.match(page.element("#budget-status").textContent, /of 11 selected models/);
    assert.match(page.element("#results").innerHTML, /Gemini 3\.1 Pro/);
    assert.match(page.element("#results").innerHTML, /Google \(gemini-3-1-pro\)/);
    assert.match(page.element("#results").innerHTML, /No snapshot benchmark data/);
    assert.equal(page.evaluate("monthlyCost(rosterOnlyComparisonRows().find(row => row.model_id === 'composer-2-5'))"), 22.5);
    assert.equal(page.evaluate("monthlyCost(rosterOnlyComparisonRows().find(row => row.model_id === 'gemini-3-1-pro'))"), 100);
    assert.match(page.element("#pricing-section").innerHTML, /gemini-3-1-pro/);
    assert.match(page.element("#view-yaml").value, /^version: 1\n/);
    assert.doesNotMatch(page.element("#view-yaml").value, /^#/m);
    assert.match(page.evaluate("dumpView(state.view, true)"), /Benchmark data and leaderboard rankings/);
    assert.equal(page.evaluate("JSON.stringify(parseViewYaml(dumpView(state.view)))"), page.evaluate("JSON.stringify(state.view)"));
  });

  check("monthly estimates and inclusive budget boundary", () => {
    const page = dashboard();
    page.evaluate("var opus = state.summaries.find(row => row.model_id === 'claude-opus-5')");
    assert.equal(page.evaluate("monthlyCost(opus)"), 225);
    page.setBudget(225);
    assert.equal(page.evaluate("withinBudget(opus)"), true);
    page.setBudget(224);
    assert.equal(page.evaluate("withinBudget(opus)"), false);
  });

  check("manual budget, slider, YAML, and saved view stay synchronized", () => {
    const page = dashboard();
    const amount = page.element("#monthly-budget-amount");
    amount.value = 217;
    amount.listeners.input();
    assert.equal(page.element("#monthly-budget").value, "217");
    assert.equal(page.element("#monthly-budget-amount").value, "217");
    assert.equal(JSON.parse(page.storage.get("modelagency-view-v1")).monthly_budget_usd, 217);
    assert.match(page.element("#view-yaml").value, /monthly_budget_usd: 217/);
    const restored = dashboard(JSON.parse(page.storage.get("modelagency-view-v1")));
    assert.equal(restored.element("#monthly-budget-amount").value, "217");
    page.setBudget(125);
    assert.equal(amount.value, "125");
    page.element("#view-yaml").value = page.evaluate("dumpView({...state.view,monthly_budget_usd:275})");
    page.element("#apply-yaml").listeners.click();
    assert.equal(amount.value, "275");
    assert.equal(page.element("#monthly-budget").value, "275");
  });

  check("invalid manual amounts preserve the budget and recover cleanly", () => {
    const page = dashboard();
    const amount = page.element("#monthly-budget-amount");
    for (const value of ["", "-1", "5001", "12.5", "invalid"]) {
      amount.value = value;
      amount.listeners.input();
      assert.equal(amount.attributes["aria-invalid"], "true");
      assert.match(page.element("#budget-amount-error").textContent, /last valid budget/);
      assert.equal(page.evaluate("state.view.monthly_budget_usd"), 300);
      assert.equal(page.element("#monthly-budget").value, "300");
    }
    page.setBudget(150);
    assert.equal(amount.value, "150");
    assert.equal(amount.attributes["aria-invalid"], "false");
    assert.equal(page.element("#budget-amount-error").textContent, "");
    page.element("#reset-view").listeners.click();
    assert.equal(amount.value, "300");
  });

  check("manual entry supports zero and the unlimited endpoint", () => {
    const page = dashboard();
    const amount = page.element("#monthly-budget-amount");
    amount.value = 0;
    amount.listeners.input();
    assert.match(page.element("#suggestions").innerHTML, /No priced models fit/);
    amount.value = 5000;
    amount.listeners.input();
    assert.equal(page.element("#monthly-budget-amount").value, "5000");
    assert.equal(page.element("#monthly-budget").value, "5000");
  });

  check("recommendations disclose the actual arithmetic and fit label", () => {
    const page = dashboard();
    assert.match(page.element("#suggestions").innerHTML, /Best Daily Driver Fit/);
    assert.match(page.element("#suggestions").innerHTML, /href="#cost-calculation-heading"/);
    assert.doesNotMatch(page.element("#suggestions").innerHTML, /<details class="cost-calculation">/);
    const sol = page.evaluate("monthlyCalculation(state.summaries.find(row => row.model_id === 'gpt-5-6-sol'))");
    assert.match(sol, /View cost calculation/);
    assert.match(sol, /20M input × \$5\/1M \+ 5M output × \$30\/1M = \$250\/month/);
    assert.match(page.element("#pricing-section").innerHTML, /Cost calculation/);
    assert.match(page.element("#pricing-section").innerHTML, /20M input and 5M output tokens per month/);
    assert.match(page.element("#pricing-section").innerHTML, /not a subscription price or measured task cost/);
    assert.match(page.element("#pricing-section").innerHTML, /View full token pricing list/);
    assert.match(page.element("#pricing-section").innerHTML, /pricing\.html#pricing-overview/);
    assert.match(page.element("#pricing-section").innerHTML, /composer-2-5/);
  });

  check("BenchLM metrics and workload mix stay source-owned", () => {
    const page = dashboard();
    assert.match(page.element("#benchlm-metrics").innerHTML, /GPT-5\.6 Luna/);
    assert.match(page.element("#benchlm-metrics").innerHTML, /84\.7/);
    assert.match(page.element("#benchlm-metrics").innerHTML, /9 of 11 selected models have BenchLM metrics/);
    assert.match(page.element("#suggestions").innerHTML, /<strong>84\.1\/100<\/strong><span>BenchLM agentic score<\/span>/);
    assert.match(page.element("#suggestions").innerHTML, /<strong>84\.7\/100<\/strong><span>BenchLM Terminal-Bench 2\.0<\/span>/);
    assert.match(page.element("#suggestions").innerHTML, /Cross-work fit; BenchLM score\./);
    assert.equal(page.evaluate("benchlmMetricValue(state.summaries.find(row => row.model_id === 'gpt-5-6-luna'), 'benchlm_overall')"), 64.65);
    assert.equal(page.evaluate("portfolioRecommendations(filteredSummaryRows()).allocations.map(row => row.share_percent).join(',')"), "10,30,60");
    assert.equal(page.evaluate("portfolioRecommendations(filteredSummaryRows()).allocations[0].row.model_id"), "gpt-6-astra");
    assert.equal(page.evaluate("portfolioRecommendations(filteredSummaryRows()).allocations.every(allocation => allocation.options.length >= 2)"), true);
    assert.equal(page.evaluate("portfolioRecommendations(filteredSummaryRows()).allocations.every(allocation => allocation.options[0].selected)"), true);
    assert.match(page.element("#suggestions").innerHTML, /portfolio-option/);
    assert.match(page.element("#suggestions").innerHTML, /Alternative/);
    assert.match(page.element("#suggestions").innerHTML, /BenchLM overall score/);
    assert.match(page.element("#suggestions").innerHTML, /Recommended workload mix/);
    assert.match(page.element("#suggestions").innerHTML, /portfolio-header-meta[\s\S]*Estimated allocation:/);
    assert.doesNotMatch(page.element("#suggestions").innerHTML, /portfolio-header-meta[\s\S]*<span class="pill">\$300 budget<\/span>/);
    assert.doesNotMatch(page.element("#suggestions").innerHTML, /portfolio-grid[\s\S]*portfolio-total/);
    assert.match(page.element("#suggestions").innerHTML, /recommendation-score[\s\S]*recommendation-footer-row[\s\S]*recommendation-cost-calculation[\s\S]*recommendation-supporting/);
  });

  check("comparison rows show provider and slug beneath each model", () => {
    const page = dashboard();
    assert.match(page.element("#results").innerHTML, /<small class="model-provider">OpenAI \(gpt-5-6-sol\)<\/small>/);
    assert.match(page.element("#results").innerHTML, /class="comparison-evidence-row" hidden/);
    assert.match(page.element("#results").innerHTML, /colspan="13"/);
  });

  check("domain quality stays source-ranked when high-end models exceed budget", () => {
    const page = dashboard();
    page.evaluate("state.view.monthly_input_tokens=40000000;state.view.monthly_output_tokens=20000000;render()");
    const engineering = JSON.parse(page.evaluate("JSON.stringify(domainRecommendationRows(filteredSummaryRows(), 'engineering').map(([label,row]) => [label,row.model_id]))"));
    assert.deepEqual(engineering, [["best_quality", "gpt-5-6-sol"], ["best_value", "gpt-5-6-luna"]]);
    assert.match(page.element("#suggestions").innerHTML, /GPT-5\.6 Sol/);
    assert.match(page.element("#suggestions").innerHTML, /Est\. \$800\/month/);
    assert.doesNotMatch(page.element("#suggestions").innerHTML, /Est\. \$800\/month · Over budget/);
  });

  check("BenchLM metrics sort by Overall by default", () => {
    const page = dashboard();
    assert.equal(page.evaluate("state.benchlmSort"), "benchlm_overall");
    assert.equal(page.evaluate("state.benchlmDirection"), "desc");
    const metrics = page.element("#benchlm-metrics");
    const sortableFields = ["model_name", "benchlm_agentic", "terminal_bench_2", "browsecomp", "osworld_verified", "benchlm_overall"];
    assert.deepEqual(metrics.children.map((button) => button.dataset.benchlmSort), sortableFields);
    const body = metrics.innerHTML.match(/<tbody>([\s\S]*)<\/tbody>/)[1];
    assert.ok(body.indexOf("GPT-6 Astra") < body.indexOf("Claude Opus 5"));
    const overall = metrics.children.find((button) => button.dataset.benchlmSort === "benchlm_overall");
    overall.listeners.click();
    assert.equal(page.evaluate("state.benchlmDirection"), "asc");
    const ascendingBody = page.element("#benchlm-metrics").innerHTML.match(/<tbody>([\s\S]*)<\/tbody>/)[1];
    assert.ok(ascendingBody.indexOf("GPT-5.6 Luna") < ascendingBody.indexOf("GPT-6 Astra"));
  });

  check("BenchLM metrics follow model selection", () => {
    const page = dashboard();
    assert.match(page.element("#benchlm-metrics").innerHTML, /Claude Opus 5/);
    const opus = page.element("#model-filters").children.find((input) => input.dataset.filterValue === "claude-opus-5");
    assert.ok(opus);
    opus.checked = false;
    opus.listeners.change();
    assert.equal(page.element("#model-count").textContent, "10 selected");
    assert.match(page.element("#benchlm-metrics").innerHTML, /8 of 10 selected models have BenchLM metrics/);
    assert.doesNotMatch(page.element("#benchlm-metrics").innerHTML, /Claude Opus 5/);
  });

  check("model-level execution scope is implicit", () => {
    const page = dashboard();
    assert.equal(page.evaluate("JSON.stringify([...selectedAgentValues()])"), '["model-level"]');
    assert.equal(page.element("#status").textContent, "11 of 21 models");
    assert.doesNotMatch(page.element("#suggestions").innerHTML, /No agent scope selected/);
    assert.doesNotMatch(readFileSync(new URL("../site/index.html", import.meta.url), "utf8"), /agents-heading/);
  });

  check("BenchLM metrics show selected models with partial evidence", () => {
    const page = dashboard();
    const opus = page.element("#model-filters").children.find((input) => input.dataset.filterValue === "claude-opus-4-6");
    assert.ok(opus);
    opus.checked = true;
    opus.listeners.change();
    assert.match(page.element("#benchlm-metrics").innerHTML, /Claude Opus 4\.6/);
    assert.match(page.element("#benchlm-metrics").innerHTML, /10 of 12 selected models have BenchLM metrics/);
  });

  check("BenchLM metrics explain roster models without source rows", () => {
    const page = dashboard();
    assert.match(page.element("#benchlm-metrics").innerHTML, /No BenchLM metrics published for Composer 2\.5 \(Cursor\) \(composer-2-5\)/);
  });

  check("model selection matrix keeps BenchLM counts synchronized", () => {
    const initial = dashboard();
    const modelIds = initial.element("#model-filters").children.map((input) => input.dataset.filterValue);
    for (const modelId of modelIds) {
      const page = dashboard();
      const input = page.element("#model-filters").children.find((candidate) => candidate.dataset.filterValue === modelId);
      input.checked = !input.checked;
      input.listeners.change();
      const selectedCount = page.evaluate("selectedValues('model-filters').size");
      const metricCount = page.evaluate("state.benchlmMetrics.records.filter(record => selectedValues('model-filters').has(record.model_id)).length");
      assert.match(page.element("#benchlm-metrics").innerHTML, new RegExp(`${metricCount} of ${selectedCount} selected models have BenchLM metrics`));
    }
  });

  check("workload mix stays visible when the selected roster needs reuse", () => {
    const page = dashboard();
    page.evaluate("state.view.monthly_input_tokens=40000000;state.view.monthly_output_tokens=20000000;var selectedRoster=filteredSummaryRows().filter(row=>!['claude-sonnet-5','gpt-5-6-terra','gemini-3-6-flash','grok-4-6'].includes(row.model_id));var mix=portfolioRecommendations(selectedRoster)");
    assert.equal(page.evaluate("mix.reusedModel"), true);
    assert.match(page.evaluate("portfolioCard(selectedRoster)"), /selected model is reused/);
  });

  check("overall quality keeps Grok in the balanced tier", () => {
    const page = dashboard();
    page.evaluate("state.view.monthly_input_tokens=40000000;state.view.monthly_output_tokens=20000000;var selectedRoster=filteredSummaryRows().filter(row=>['claude-fable-5','claude-opus-4-8','claude-opus-5','gpt-5-6-luna','gpt-5-6-sol','gpt-6-astra','gemini-3-6-flash','grok-4-6'].includes(row.model_id));var mix=portfolioRecommendations(selectedRoster)");
    assert.equal(page.evaluate("mix.allocations[1].row.model_id"), "grok-4-6");
    assert.equal(page.evaluate("mix.allocations[1].quality.score"), 70.08);
    assert.equal(page.evaluate("mix.allocations[1].quality.source"), "BenchLM overall score");
    assert.match(page.evaluate("portfolioCard(selectedRoster)"), /Grok 4\.6/);
  });

  check("slider changes winners and persists without altering evidence", () => {
    const page = dashboard();
    const before = page.evaluate("JSON.stringify([state.records, state.summaries, state.leaderboard])");
    assert.equal(page.evaluate("recommendationRows(recommendationSourceRows().filter(row => row.category === 'daily_driver'))[0][1].model_id"), "gpt-5-6-sol:daily-driver");
    page.setBudget(100);
    assert.equal(page.evaluate("recommendationRows(recommendationSourceRows().filter(row => row.category === 'daily_driver'))[0][1].model_id"), "gpt-5-6-luna:daily-driver");
    assert.match(page.element("#results").innerHTML, /Over budget/);
    assert.equal(page.element("#status").textContent, "11 of 21 models");
    assert.equal(JSON.parse(page.storage.get("modelagency-view-v1")).monthly_budget_usd, 100);
    assert.equal(before, page.evaluate("JSON.stringify([state.records, state.summaries, state.leaderboard])"));
    const restored = dashboard(JSON.parse(page.storage.get("modelagency-view-v1")));
    assert.equal(restored.element("#monthly-budget-amount").value, "100");
  });

  check("zero budget never falls back to over-budget recommendations", () => {
    const page = dashboard();
    page.setBudget(0);
    assert.match(page.element("#suggestions").innerHTML, /<article class="card portfolio-card">[\s\S]*No priced models fit this budget/);
    assert.equal(page.evaluate("recommendationRows(recommendationSourceRows()).length"), 0);
    assert.equal(page.evaluate("domainRecommendationRows(filteredSummaryRows(), 'engineering').length"), 0);
  });

  check("unknown prices, genuine zero prices, and fractions of a cent", () => {
    const page = dashboard();
    page.setBudget(0);
    assert.equal(page.evaluate("withinBudget({input_price_per_million_usd:null,output_price_per_million_usd:0})"), false);
    assert.equal(page.evaluate("withinBudget({input_price_per_million_usd:0,output_price_per_million_usd:0})"), true);
    assert.equal(page.evaluate("withinBudget({input_price_per_million_usd:0.000001,output_price_per_million_usd:0})"), false);
    assert.equal(page.evaluate("formatDollars(0.004)"), "<$0.01");
  });

  check("5000+ removes the cap explicitly", () => {
    const page = dashboard();
    page.setBudget(5000);
    assert.equal(page.element("#monthly-budget-amount").value, "5000");
    assert.match(page.element("#budget-status").textContent, /No budget cap/);
    assert.equal(page.evaluate("withinBudget({input_price_per_million_usd:1000,output_price_per_million_usd:1000})"), true);
    assert.equal(page.evaluate("withinBudget({})"), true);
    assert.equal(page.evaluate("bestMonthlyValue([{model_name:'unknown',score:100}], row=>row.score)"), null);
  });

  check("usage inputs update estimates and retain the last valid value", () => {
    const page = dashboard();
    const input = page.element("#monthly-input-million");
    input.value = 40;
    input.listeners.input();
    assert.equal(page.evaluate("monthlyCost(state.summaries.find(row => row.model_id === 'claude-opus-5'))"), 325);
    assert.equal(JSON.parse(page.storage.get("modelagency-view-v1")).monthly_input_tokens, 40000000);
    input.value = "";
    input.listeners.input();
    assert.match(page.element("#budget-error").textContent, /last valid estimate/);
    assert.equal(page.evaluate("state.view.monthly_input_tokens"), 40000000);
    input.value = 0;
    input.listeners.input();
    assert.equal(page.evaluate("state.view.monthly_input_tokens"), 0);
    assert.equal(page.element("#budget-error").textContent, "");
  });

  check("Best Value uses the selected input/output workload", () => {
    const page = dashboard();
    page.evaluate("var candidates = [{model_name:'Input saver',score:50,input_price_per_million_usd:1,output_price_per_million_usd:20},{model_name:'Output saver',score:50,input_price_per_million_usd:10,output_price_per_million_usd:1}]");
    page.evaluate("state.view.monthly_input_tokens=20000000;state.view.monthly_output_tokens=0");
    assert.equal(page.evaluate("bestMonthlyValue(candidates,row=>row.score).model_name"), "Input saver");
    page.evaluate("state.view.monthly_input_tokens=0;state.view.monthly_output_tokens=20000000");
    assert.equal(page.evaluate("bestMonthlyValue(candidates,row=>row.score).model_name"), "Output saver");
  });

  check("coverage preference applies after affordability", () => {
    const page = dashboard();
    page.evaluate("state.view.monthly_input_tokens=1000000;state.view.monthly_output_tokens=0;var candidates=[{category:'daily_driver',model_name:'Broad',coverage:4,score:50,input_price_per_million_usd:20,output_price_per_million_usd:0},{category:'daily_driver',model_name:'Sparse',coverage:2,score:99,input_price_per_million_usd:10,output_price_per_million_usd:0}]");
    assert.equal(page.evaluate("recommendationRows(candidates)[0][1].model_name"), "Broad");
    page.setBudget(10);
    assert.equal(page.evaluate("recommendationRows(candidates)[0][1].model_name"), "Sparse");
  });

  check("old saved views and intentional empty selections survive", () => {
    const page = dashboard({ ...fixture.default_view, models: [], monthly_budget_usd: undefined,
      monthly_input_tokens: undefined, monthly_output_tokens: undefined });
    assert.equal(page.element("#monthly-budget-amount").value, "300");
    assert.equal(page.element("#status").textContent, "0 of 21 models");
    assert.match(page.element("#suggestions").innerHTML, /No recommendations match/);
  });

  check("invalid YAML is rejected and reset restores the budget", () => {
    const page = dashboard();
    page.setBudget(100);
    page.element("#view-yaml").value = "version: 1\nmonthly_budget_usd: -1\n";
    page.element("#apply-yaml").listeners.click();
    assert.match(page.element("#view-status").textContent, /YAML not applied/);
    assert.equal(page.evaluate("state.view.monthly_budget_usd"), 100);
    page.element("#reset-view").listeners.click();
    assert.equal(page.element("#monthly-budget-amount").value, "300");
    assert.match(page.element("#view-yaml").value, /^version: 1\n/);
  });

  return `${passed.length} dashboard budget checks passed`;
}
