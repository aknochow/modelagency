# Ranking comparison · 2026-09-11

Baseline: the preserved working tree before the canonical-layer changes.
After: the offline build with canonical evidence precedence, the dated
BenchLM metrics snapshot, effort-aware fields, and the workload-mix UI.
The build remains deterministic and offline; no network refresh is required.

## Default view: source-backed Daily Driver quality scores

| Configuration | Before | After | Coverage | Basis |
| --- | ---: | ---: | ---: | --- |
| gpt-5-6-sol | 73.3 | 92.0 | 4/8 | BenchLM agentic |
| gpt-6-astra | 72.9 | 91.5 | 3/8 | BenchLM agentic |
| claude-opus-5 | 75.3 | 90.8 | 5/8 | BenchLM agentic |
| gpt-5-6-terra | 51.9 | 87.4 | 4/8 | BenchLM agentic |
| gpt-5-6-luna | 28.3 | 84.1 | 4/8 | BenchLM agentic |
| gemini-3-6-flash | 52.3 | 83.0 | 2/8 | BenchLM agentic |
| claude-sonnet-5 | 33.4 | 82.0 | 4/8 | BenchLM agentic |
| claude-opus-4-8 | 43.1 | 80.4 | 5/8 | BenchLM agentic |
| grok-4-6 | 37.2 | 70.1 | 1/8 | BenchLM overall fallback |

All 63 normalized evidence records remain byte-for-byte unchanged. The
after-view uses exact BenchLM agentic scores for models with published values;
Grok now uses its source-owned BenchLM Overall score when the agentic lane is
unavailable, before any local fallback. Domain cards similarly prefer
Terminal-Bench 2.0, BrowseComp, and OSWorld-Verified where applicable, while
Media remains derived. Score ranges are populated from observed configurations
only; the current normalized fixture has no effort-specific production rows,
so each range is currently a single value. The default view contains nine
models; saved browser views can select a different roster.

## BenchLM source metrics

The dashboard now displays source-owned BenchLM values instead of implying
that modelagency percentiles are BenchLM ranks. Values below are the tracked
default roster, retrieved 2026-09-11 from the September 10, 2026 BenchLM
pages. An em dash means the source does not publish that exact value for the
model.

| Model | Agentic | Terminal-Bench 2.0 | BrowseComp | OSWorld-Verified | Overall |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPT-5.6 Sol | 92.0 (#1) | 91.9 | 92.2 | — | 80.63 (#5) |
| GPT-6 Astra | 91.5 (#2) | — | 91.5 | — | 84.08 (#2) |
| Claude Opus 5 | 90.8 (#3) | — | 90.8 | — | 81.97 (#3) |
| GPT-5.6 Terra | 87.4 (#7) | 87.4 | 87.5 | — | 71.13 (#11) |
| GPT-5.6 Luna | 84.1 (#13) | 84.7 | 83.3 | — | 64.65 (#38) |
| Gemini 3.6 Flash | 83.0 (#16) | — | — | 83.0 | 68.39 (#23) |
| Claude Sonnet 5 | 82.0 (#19) | 80.4 | 84.7 | 81.2 | 69.84 (#18) |
| Claude Opus 4.8 | 80.4 (#23) | 74.6 | 84.3 | 83.4 | 72.22 (#8) |
| Grok 4.6 | — | — | — | — | 70.08 (#16) |

The source pages remain the evidence layer: [agentic leaderboard](https://benchlm.ai/llm-agent-benchmarks), [overall leaderboard](https://benchlm.ai/), [Terminal-Bench 2.0](https://benchlm.ai/benchmarks/terminal-bench-2), [BrowseComp](https://benchlm.ai/benchmarks/browsecomp), and [OSWorld-Verified](https://benchlm.ai/benchmarks/osworld-verified).

## $300 workload mix

Using 20M input and 5M output tokens per month, the source-score-led mix is:

| Workload share | Tier | Model | Quality signal | Allocated estimate |
| ---: | --- | --- | ---: | ---: |
| 10% | Specialist | GPT-6 Astra | 84.1 BenchLM overall | $45.00 |
| 30% | Everyday | GPT-5.6 Terra | 71.1 BenchLM overall | $37.50 |
| 60% | High-volume | GPT-5.6 Luna | 64.7 BenchLM overall | $30.00 |

Estimated allocation is $112.50/month, leaving $187.50 under the cap. Shares
describe workload, not quota spend; each full-workload estimate is calculated
from the snapshot token prices before the share is applied.

## Canonical BenchLM ranking lanes

The full published ranking-lane export remains unavailable in the checked-in
snapshot. The dashboard does not reconstruct it from the source metrics or
derived standings; the optional lane panel stays explicitly unavailable.

## Validation

Offline unit tests, dashboard rendering/selection/lane logic checks, catalog
validation, and whitespace checks pass. The local server serves the updated
preview at http://127.0.0.1:18765/?v=20260911-10. Browser automation was not
available in this environment, so final layout verification remains manual.
