# Sources, rights, and attribution

This project treats provenance as part of the data model, not as a footer added
after the fact.

## Publication rules

- Store only scores, model identifiers, pricing facts, and derived values that
  the source permits us to redistribute.
- Do not mirror source HTML, prose, screenshots, logos, benchmark prompts,
  trajectories, or raw evaluation artifacts.
- Every result links to both the aggregator record and the original benchmark
  source where one exists.
- Every dashboard row includes attribution; weekly reports include both links.
- A source without clear redistribution permission is `link_only` or
  `reference_only`, never silently ingested.
- Artificial Analysis fields are excluded from the BenchLM adapter because the
  current Artificial Analysis data terms restrict raw redistribution and
  substantially similar public competitive products without written consent.

## Current source matrix

| Source | Status | Use | Required credit |
|---|---|---|---|
| [BenchLM](https://benchlm.ai/data) | Approved with attribution | Selected machine-readable scores, source-owned leaderboard metrics, and token prices | `Source: BenchLM.ai (https://benchlm.ai), retrieved YYYY-MM-DD`; plus original benchmark credit |
| [Harbor Terminal-Bench](https://github.com/harbor-framework/terminal-bench) | Approved with attribution | Aggregate leaderboard accuracy, effort, and resource totals; no task artifacts | `Source: Harbor Terminal-Bench leaderboard (https://hub.harborframework.com/datasets/terminal-bench/terminal-bench/latest?tab=leaderboard&leaderboard=4-0-0), retrieved YYYY-MM-DD`; plus Terminal-Bench contributor credit |
| [DeepSWE](https://deepswe.datacurve.ai/) | Permission required | Link-only reference until Datacurve confirms redistribution terms | DeepSWE by Datacurve link |
| [Artificial Analysis Models](https://artificialanalysis.ai/models) | Reference-only | Methodology/reference point; no data ingestion | Link only; no mirrored metrics |
| [Artificial Analysis Coding Agents](https://artificialanalysis.ai/agents/coding-agents) | Reference-only | Methodology/reference point; no data ingestion | Link only; no mirrored metrics |

BenchLM states that its dataset is MIT licensed and requests attribution, while
also noting that underlying benchmark results belong to their original
publishers. We preserve those original evidence URLs rather than presenting
the aggregated scores as our own.

BenchLM is the canonical leaderboard and evidence layer. Its dataset and
[terms](https://benchlm.ai/terms) were reviewed on 2026-09-10. Published ranks,
overall scores, and verified/provisional lanes remain separate from local
fallback scores; matching quality cards use the exact source values. The
checked-in metrics snapshot was retrieved on 2026-09-11 from the published
September 10 pages; the standard attribution is:

> Benchmark data and leaderboard rankings from BenchLM.ai, retrieved
> 2026-09-11. BenchLM dataset licensed under MIT. Underlying benchmark
> results remain attributed to their original publishers.

Matching benchmark/model/configuration results prefer BenchLM during ranking
deduplication. Source refreshes preserve both records in normalized storage.
Only sources marked approved with permitted redistribution enter the build.

Harbor's Terminal-Bench repository and aggregate leaderboard export are
Apache-2.0 licensed. The adapter stores only aggregate leaderboard rows. The
benchmark's own canary and task-level licensing restrictions are honored by
not importing or redistributing task prompts, solutions, trajectories, or
artifacts. Cost per task is explicitly derived from Harbor's reported total
submission cost divided by the published task count; it is not presented as a
single-run observed task cost.

This policy is an operational safeguard, not legal advice. When a source's
terms change or remain ambiguous, stop ingestion and change its catalog entry
to `permission_required`.

## Project-owned presentation assets

The dashboard's Project Felt presentation layer is separate from benchmark
data provenance. PatternFly foundation CSS is vendored with an Apache-2.0
notice; modelagency's own layout and behavior are MIT licensed. See
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) for the exact asset
commit and license links.
