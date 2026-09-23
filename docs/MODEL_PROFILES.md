# Model profiles and configuration pricing

Yes: modelagency should have a small static profile page for every tracked
model configuration. The page should be generated from checked-in metadata and
the normalized evidence, not rendered from a live provider API.

## Identity

The provider model ID and the evaluated configuration are separate fields:

```yaml
model_id: gpt-5-6-luna
configuration_id: gpt-5-6-luna@high
effort_level: high
display_name: GPT-5.6 Luna (high)
```

If no effort or other runtime setting is present, `configuration_id` is the
provider model ID. If a source reports Luna at medium, high, xhigh, or max, each
configuration gets its own evidence rows, aggregate scores, recommendation
eligibility, and cost record. A high/xhigh/max result must not be merged into a
medium result.

## Profile fields

Each generated page should provide:

- provider and canonical model/configuration IDs;
- official model and API documentation links;
- modalities and supported tool surfaces;
- context and maximum-output limits, with the serving surface named;
- pricing records by serving surface, region, billing mode, and context tier;
- native category aggregates, the BenchLM-backed Daily Driver quality signal
  (or labeled BenchLM Overall/local fallback), and coverage;
- benchmark evidence, original benchmark links, retrieval dates, and required
  attribution/credit.

## Pricing contract

Pricing is not a single property of a model. It is a list of records keyed by
at least:

```yaml
surface: anthropic_api | vertex_ai | bedrock | other
scope: global | us_only | region-specific
billing_mode: standard | batch | cache_write | cache_hit
context_tier: standard | long_context
input_price_per_million_usd: 5.0
output_price_per_million_usd: 25.0
source_url: https://...
retrieved_date: YYYY-MM-DD
```

The dashboard cost tier is only a deterministic token-price proxy. It must
identify which pricing record it uses and must never imply that token price is
task cost. Effort can also affect task cost through token usage even when the
provider's per-token rate is unchanged, so effort-specific usage data belongs
in a separate task-cost record.

This distinction is necessary in practice. Anthropic's Opus 4.6 announcement
lists direct Claude API pricing of $5 input / $25 output per million tokens,
while Google's managed Agent Platform pricing page lists Claude Opus 4.6 at
$5.50 / $27.50 and Claude Sonnet 4.6 at $3.30 / $16.50. The Google page also
has separate batch and cache SKUs. These are separate, dated pricing records,
not interchangeable replacements:

- [Anthropic Claude Opus 4.6 pricing](https://www.anthropic.com/news/claude-opus-4-6)
- [Google Agent Platform generative-AI pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)
- [Google's Vertex AI Claude 4.6 availability announcement](https://cloud.google.com/blog/products/ai-machine-learning/expanding-vertex-ai-with-claude-opus-4-6)

## Current state

Dashboard model names now link to their BenchLM profiles. BenchLM is the
canonical leaderboard and evidence layer; a future local profile must retain
its dated attribution, exact published ranks and lanes, and separate labels
for source-backed values and modelagency-derived fallbacks. See
[`CANONICAL_LEADERBOARD.md`](CANONICAL_LEADERBOARD.md).

The aggregate dashboard now carries configuration-aware IDs and optional
effort levels. The checked-in benchmark fixture does not yet contain separate
Luna medium/high/xhigh/max measurements, so those settings are not assigned
invented scores or recommendations. The next profile implementation should
populate only provider-verified metadata and source-permitted benchmark data.

The initial published benchmark rows come from BenchLM. DeepSWE remains
link-only pending redistribution permission, and Artificial Analysis remains a
reference-only source under its current terms; see [`SOURCES.md`](SOURCES.md).

The current roster pricing snapshot also covers Composer 2.5 (Cursor's
standard API rate) and Gemini 3.1 Pro (the standard rate for prompts up to
200K). Each record retains its BenchLM profile URL, retrieval date, and a note
for alternate context or speed tiers; these prices are budgeting inputs, not
measured task costs.
