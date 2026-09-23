# Ideas

Product ideas and integration opportunities to revisit. These are not part of
the current dashboard contract until they are explicitly scoped and implemented.

## BenchLM integrations

Source: [BenchLM Data & Embed](https://benchlm.ai/embed). BenchLM's embed page
provides live widgets with a visible attribution link. Any future integration
must preserve that attribution, keep the external source clearly labeled, and
avoid replacing the deterministic local snapshot used by the dashboard.

### Compare widget — high priority

Add a `Compare` action for model cards and table rows. When two models are
selected, open a modal or dedicated view containing the BenchLM comparison
iframe, for example:

```html
<iframe
  src="https://benchlm.ai/embed/compare?a=<model-a>&b=<model-b>&theme=<theme>"
  title="BenchLM model comparison"
  loading="lazy"
></iframe>
```

Acceptance notes:

- Map modelagency IDs to BenchLM public slugs before building the URL.
- Require exactly two comparable models and explain when a model has no
  BenchLM comparison slug.
- Keep BenchLM's generated attribution link visible and label the panel as a
  live external view.
- Keep our local BenchLM snapshot, scores, budget logic, and recommendations
  as the dashboard source of truth.
- Provide a clear fallback link to the comparison page when network access or
  iframe loading is unavailable.
- Test light/dark widget themes, keyboard focus, responsive sizing, and a
  no-network/offline state.

## Widget inventory

### Leaderboard widget

Live overall leaderboard iframe with configurable row count, light/dark theme,
category selection, and an optional 90% score-interval (BenchAlign) column.
Potential use: a clearly labeled live reference on the Sources page, not a
replacement for the selected-model table.

### Comparison widget

Live two-model comparison iframe with public scores, evidence status, rank,
category rows, and links to the comparison evidence. This is the preferred
next integration because it complements modelagency's budget and workload
recommendations.

### Token Price Index widget

Live frontier/mid-tier/budget token-price index chart. Potential use: a pricing
context panel or a link from the budget notes; do not mix its index with our
per-model cost estimate without documenting the different methodology.

### Context Window chart widget

Live comparison of documented context windows for BenchLM's default model set.
Potential use: an optional model-detail or notes panel; keep it separate from
the workload budget calculation.

## Non-widget opportunities

- **Machine-readable refresh:** evaluate BenchLM's JSON/CSV downloads for a
  deliberate, cached snapshot refresh workflow. Preserve offline fixtures and
  validation tests; never make page rendering depend on the network.
- **API-backed refresh:** consider the documented leaderboard, pricing,
  comparison, and benchmark endpoints only for an explicit refresh tool. Cache
  results, respect the published rate limits, and record retrieval timestamps.
- **Attribution link:** keep a prominent `View live BenchLM` link even when no
  iframe is embedded, so users can inspect current rankings and evidence.

## Guardrails

- BenchLM's published dataset license and terms permit product use with
  attribution; underlying benchmark results remain attributed to their
  original publishers. Re-check the source terms before each new integration.
- Live embeds are network-dependent and can diverge from our dated local
  snapshot. Display freshness and source context rather than silently mixing
  values.
- Do not copy benchmark prompts, trajectories, raw evaluation artifacts, or
  source-owned material that is not cleared for redistribution.
