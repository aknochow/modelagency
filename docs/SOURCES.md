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
| [BenchLM](https://benchlm.ai/data) | Approved with attribution | Selected machine-readable scores and token prices | `Source: BenchLM.ai (https://benchlm.ai), retrieved YYYY-MM-DD`; plus original benchmark credit |
| [DeepSWE](https://deepswe.datacurve.ai/) | Permission required | Link-only reference until Datacurve confirms redistribution terms | DeepSWE by Datacurve link |
| [Artificial Analysis Models](https://artificialanalysis.ai/models) | Reference-only | Methodology/reference point; no data ingestion | Link only; no mirrored metrics |
| [Artificial Analysis Coding Agents](https://artificialanalysis.ai/agents/coding-agents) | Reference-only | Methodology/reference point; no data ingestion | Link only; no mirrored metrics |

BenchLM states that its dataset is MIT licensed and requests attribution, while
also noting that underlying benchmark results belong to their original
publishers. We preserve those original evidence URLs rather than presenting
the aggregated scores as our own.

This policy is an operational safeguard, not legal advice. When a source's
terms change or remain ambiguous, stop ingestion and change its catalog entry
to `permission_required`.
