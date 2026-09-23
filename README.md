# modelagency

`modelagency` is a deterministic, provenance-first index of public model and
agent benchmark results, pricing, and task recommendations.

BenchLM is the canonical leaderboard and evidence layer. modelagency adds
personal views, work-category groupings, and explicitly derived recommendations.
Published BenchLM ranks and scores are source-owned values; filtering never
renumbers them or replaces them with a modelagency index.

> Benchmark data and leaderboard rankings from BenchLM.ai, retrieved
> 2026-09-11. BenchLM dataset licensed under MIT. Underlying benchmark
> results remain attributed to their original publishers.

See the [BenchLM dataset and license](https://benchlm.ai/data). modelagency is
independent and is not affiliated with or endorsed by BenchLM.

The project deliberately does not call language models. CI validates the
checked-in source snapshots, normalizes names, calculates quality/cost views,
renders a static dashboard, and produces a weekly report. Source refreshes are
explicit developer commands rather than an unattended deployment step.
The dashboard uses PatternFly v6's Project Felt theme with a small
modelagency-specific token layer; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
for the vendored asset attribution.

The `daily_driver` view uses the published BenchLM agentic score directly when
that source value exists (for example, Luna is 84.1/100). Models without a
published agentic value use BenchLM's published overall score as an explicit
cross-work fallback (for example, Grok 4.6 is 70.08/100). Only models without
either source value use a deterministic local fallback: each benchmark is
normalized to a mid-rank percentile, the available work-category scores are
averaged, and a 25% breadth component is applied across the eight categories.
A single-model benchmark receives a neutral percentile of 50. The fallback is
documented in `modelagency/pipeline.py`.

The dashboard matrix keeps two score meanings separate: category cells are
means of the linked benchmark scores in their native units, while the three
dashboard domains use source-backed BenchLM lanes where they fit. Engineering
prefers Terminal-Bench 2.0 and otherwise uses the BenchLM agentic score as an
explicitly labeled proxy; Management averages published BrowseComp and
OSWorld-Verified values when available; Media remains a local normalized
fallback until an approved visual/writing lane exists. The local fallback
prevents a published score such as 83.3 from being averaged directly with an
Elo score such as 1322. CI/CD is part of the schema now, but remains unscored
until an approved source provides explicit CI/CD evidence.

The `daily_driver` column remains a separate cross-work quality signal so
source-owned agentic scores, overall fallbacks, and local breadth fallbacks
stay visible. The workload mix uses BenchLM Overall as its cross-work quality
lane when available, then agentic, then the observed local range. Domain scores
include their underlying-category coverage, and the detailed evidence drawer
preserves the original benchmark scores, units, and links.

The comparison table also exposes a small source-owned BenchLM snapshot: the
agentic score, BenchLM overall score, Terminal-Bench 2.0, BrowseComp, and
OSWorld-Verified values. Those cells link to the published BenchLM evidence;
missing values stay blank. Source-backed recommendation values retain their
BenchLM provenance; local percentile fallbacks are never presented as a
BenchLM rank.

Model configurations are identified separately from the provider model ID.
When a source reports an effort setting, a configuration such as
`gpt-5-6-luna@high` remains distinct from `gpt-5-6-luna@medium`. Missing
effort-specific evidence is left missing; it is never inferred from a nearby
setting or a personal impression.

## Source and copyright policy

Every published value must have a source record containing:

- source name and canonical URL;
- retrieval timestamp and source version/build timestamp;
- original benchmark URL when an aggregator is used;
- license/terms URL and redistribution status;
- required attribution text;
- whether the value is copied, derived, or link-only.

The public site will contain facts and derived rankings only where the source
license or written permission allows redistribution. It will not mirror page
HTML, prose, screenshots, logos, benchmark prompts, trajectories, or raw
datasets without permission. Source-specific restrictions are recorded in
`catalog/sources.json` and enforced by the validator.

Artificial Analysis is currently reference-only: its current data terms
restrict raw-data redistribution and prohibit operating a substantially
similar public competitive product without prior written consent. We may link
to it and request permission, but the initial build will not ingest its data.

The initial tracked roster omits Claude Opus and Sonnet releases older than
4.6, along with explicit Claude Thinking/Adaptive reasoning profiles. Other
standard Claude families remain eligible for tracking.

Composer 2.5 and Gemini 3.1 Pro are included as roster entries. The offline
snapshot now carries dated, source-attributed token prices for both models, so
they appear in budget comparisons even when benchmark evidence is unavailable
in the local snapshot. They remain excluded from scored recommendations until
benchmark evidence is added.

BenchLM is the canonical machine-readable source because its dataset page states
that the dataset is MIT licensed. Underlying benchmark publishers still get
individual attribution; the adapter preserves those evidence URLs.

Harbor Terminal-Bench is an approved first-party aggregate source under
Apache-2.0. The adapter imports leaderboard accuracy, effort, and resource
totals only; it never imports task prompts, solutions, trajectories, or raw
benchmark artifacts. When a direct Terminal-Bench result overlaps a BenchLM
copy of the same benchmark/model/configuration, BenchLM wins deterministically.
Both source records remain stored; refreshing a publisher never deletes the
canonical evidence. Effort configurations remain separate.

The current snapshot contains 63 benchmark records plus a small, dated
BenchLM metrics snapshot. A full published ranking-lane export is still
optional; the dashboard keeps that lane unavailable rather than reconstructing
it. See
[`docs/CANONICAL_LEADERBOARD.md`](docs/CANONICAL_LEADERBOARD.md) for the local
snapshot contract and the remaining upstream integration work.

Views use each source's canonical `model_id` (for example,
`gpt-5-6-luna`) in YAML, local storage, and exports. The dashboard shows the
human-readable model name alongside that ID in the model filter.

## Monthly Budget

The dashboard's monthly API budget defaults to **$300**. The slider runs from
$0 to **$5,000+**, where the upper endpoint removes the budget cap. A numeric
field accepts an exact whole-dollar amount and stays synchronized with the
slider, YAML, and saved view. The default
workload is **20 million input tokens and 5 million output tokens per month**;
both assumptions can be edited in the sidebar and persist in saved/YAML views.

Estimated monthly cost is `input_tokens / 1M × input_price + output_tokens / 1M
× output_price`, using the snapshot's published token prices. Each candidate is
estimated separately for the full workload. The workload-mix card then assigns
10% specialist, 30% balanced, and 60% value shares; those are workload shares,
not promises to spend the same percentage of the budget. Subscriptions,
cache discounts, tool charges, and taxes are excluded.

Each recommendation has a cost-calculation disclosure showing the assumed
tokens, snapshot unit prices, and total. For example, the current defaults
estimate Opus 5 at `20 × $5 + 5 × $25 = $225/month`, and Sol at
`20 × $5 + 5 × $30 = $250/month`. These are API workload estimates, not plan
prices or predictions of how many tasks either model will complete.

The Daily Driver card labels its winner **Best Daily Driver Fit** because the
budget is an eligibility constraint and the card separates quality from value.
When BenchLM publishes an agentic score, that exact source score is shown;
otherwise the card labels the local breadth fallback. Source ranks and
benchmark scores remain unchanged. Domain quality cards rank the selected
source scores even when the winner is over budget and label that condition;
their Best Value companion remains budget eligible.

The budget limits value, Daily Driver, and workload-mix recommendations without
changing evidence, source ranks, source metrics, quality scores, or the
comparison roster. Models with missing token prices cannot be recommended under
a capped budget. Daily Driver's coverage preference applies among affordable
models; Best Value minimizes estimated monthly cost per derived score point. The
weekly report remains an unfiltered snapshot, independent of a browser's budget.
The YAML editor starts with configuration; downloaded YAML retains source
attribution.

## Local commands

```bash
python -m modelagency.cli validate
python -m modelagency.cli build
python -m modelagency.cli report
python -m modelagency.cli fetch-benchlm  # explicit network fetch
python -m modelagency.cli fetch-terminal-bench  # requires a pinned Harbor CLI
python -m modelagency.cli slack           # sends only when webhook is configured
python -m unittest discover -s tests -v
node -e "import('./tests/test_dashboard_budget.mjs').then(tests => console.log(tests.runBudgetTests()))"
```

`build` is offline by default and uses the checked-in normalized fixture. The
GitHub Pages workflow also builds from those checked-in snapshots only; run a
source refresh explicitly, review the diff, and commit the updated snapshot
before publishing it.

## Planned deployment

The generated `site/` directory is suitable for GitHub Pages or GitLab Pages.
The GitHub Pages workflow publishes the checked-in artifact without source
network access or secrets. The weekly report is Markdown first; Slack posting
remains an explicit local command when a webhook is configured.

See [`docs/SOURCES.md`](docs/SOURCES.md) for the source-by-source rights and
attribution policy.

See [`docs/MODEL_PROFILES.md`](docs/MODEL_PROFILES.md) for the planned static
per-model/per-configuration profile contract, including surface-specific
pricing for direct provider APIs and managed cloud endpoints.
