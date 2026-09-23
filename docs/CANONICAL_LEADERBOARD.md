# Canonical leaderboard contract

BenchLM owns the overall leaderboard. modelagency must not reconstruct it
from category scores, list position, or Daily Driver recommendations.

## Current integration status

The 2026-09-10 review confirmed the published dataset and terms pages:

- https://benchlm.ai/data
- https://benchlm.ai/terms

The model JSON request returned HTTP 403 Forbidden. The web reader rejected
the separately published leaderboard export as unsafe to open. These requests
were not retried through alternative access methods. No new source results
were imported, and the existing 63 benchmark records remain intact.

The exact upstream leaderboard JSON schema has not been verified. The
published overall and agentic pages are nevertheless available as source
evidence. The dashboard stores a small, fixture-backed metrics snapshot for
the tracked roster; it does not claim that this snapshot is the upstream
export schema or mirror the full dataset.

`data/normalized/benchlm_metrics.json` preserves the source-owned values used
in the dashboard’s BenchLM columns: agentic score/rank, BenchAlign overall
score/rank, and the three core agentic benchmark values. Missing values stay
null. Each benchmark value retains its original BenchLM evidence URL, and the
snapshot records the BenchLM verification date and retrieval date.

## Local normalized leaderboard snapshot

An optional `data/normalized/benchlm_leaderboard.json` is consumed by offline
validation, builds, and weekly reports. The contract is defined and validated
in `modelagency/canonical.py`. Required envelope fields are:

- `schema_version`: `"1"`.
- `source_id`: `"benchlm"`.
- `source_url`: `https://benchlm.ai/data/leaderboard.json`.
- `source_license_url`: `https://benchlm.ai/data`.
- `source_generated_at`: the upstream build timestamp.
- `retrieved_date`: the actual retrieval date, independent of build time.
- `attribution`: the project's dated BenchLM attribution.
- `records`: normalized model/configuration rows.

Each row contains `model_id`, `configuration_id`, `model_name`, `profile_url`,
`source_rank`, `source_score`, `lane`, and `evidence_status`. Rank and score
are exact source values or explicit nulls. Lanes are `provisional` and
`verified`; each configuration may have a separate row in each lane. Evidence
status retains the source's own text and is never inferred from a lane.

An explicitly named agent is part of the local configuration identity:
`model@effort@agent:agent-id`. A model-level row without an agent is not
silently treated as the same evaluation as a named agent run.

These field names describe our contract, not undocumented upstream fields.
`tests/fixtures/benchlm_canonical_contract.json` is synthetic test data and
must never be copied into production data.

The separate metrics snapshot is intentionally not used to reconstruct the
canonical ranking or to replace an unavailable ranking-lane export. It is a
source-owned display layer and quality signal: when a matching BenchLM lane is
published, the dashboard uses that exact value for the corresponding domain
or Daily Driver card. When the agentic lane is unavailable, the published
overall score is an explicitly labeled cross-work fallback; only models without
either source value retain the modelagency-derived fallback. The workload mix
uses Overall first so models with different benchmark coverage remain
comparable on one source-owned lane.

## Completing the upstream integration

Once authorized access to the published export is available, inspect its
actual structure and add a fixture-backed normalization adapter. Preserve
model/configuration identity, original evidence URLs, source build timestamp,
retrieval date, exact source score and rank, and each ranking lane. Do not
invent effort-level results or treat source benchmark scores as overall scores.

Store only approved normalized facts. Keep the model and pricing refresh
explicit, preserve the previous snapshot if retrieval fails, and compare the
before/after derived rankings before rebuilding. A missing snapshot remains
unavailable rather than falling back to a locally calculated leaderboard.
