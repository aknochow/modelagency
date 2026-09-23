"""Deterministic offline build and recommendation functions."""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import product
from pathlib import Path
from typing import Any

from .canonical import model_profile_url
from .model_policy import is_model_in_scope
from .schema import Result

DAILY_DRIVER_CATEGORY = "daily_driver"
DAILY_DRIVER_BENCHMARK_ID = "daily-driver-index"
DAILY_DRIVER_VERSION = "v1"
# The dashboard presents these three stable work domains.  The underlying
# benchmark categories remain separate so each published value can retain its
# original evidence and attribution.
DOMAIN_CATEGORIES = {
    "engineering": ("coding", "terminal", "cicd"),
    "management": ("administrative", "office", "computer_use"),
    "media": ("graphics", "visual_reasoning", "writing"),
}
TOP_LEVEL_DOMAINS = tuple(DOMAIN_CATEGORIES)
BENCHLM_AGENTIC_URL = "https://benchlm.ai/llm-agent-benchmarks"
BENCHLM_OVERALL_URL = "https://benchlm.ai/"
BENCHLM_BENCHMARK_URLS = {
    "terminal_bench_2": "https://benchlm.ai/benchmarks/terminal-bench-2",
    "browsecomp": "https://benchlm.ai/benchmarks/browsecomp",
    "osworld_verified": "https://benchlm.ai/benchmarks/osworld-verified",
}
BENCHLM_BENCHMARK_LABELS = {
    "terminal_bench_2": "Terminal-Bench 2.0",
    "browsecomp": "BrowseComp",
    "osworld_verified": "OSWorld-Verified",
}
# These mappings only use a source-published benchmark when it is a direct
# fit for the work domain. The agentic score is an explicit fallback for the
# agent-heavy Engineering and Management domains when no mapped lane is
# published; Media stays derived until an approved visual/writing lane exists.
BENCHLM_DOMAIN_BENCHMARKS = {
    "engineering": ("terminal_bench_2",),
    "management": ("browsecomp", "osworld_verified"),
    "media": (),
}
DAILY_DRIVER_CATEGORIES = (
    "administrative",
    "coding",
    "computer_use",
    "graphics",
    "office",
    "terminal",
    "visual_reasoning",
    "writing",
)
# Do not recommend a sparsely evaluated model as a daily driver when a model
# with broader evidence is available.  This is a recommendation eligibility
# rule; the published index still reports the transparent score and coverage.
DAILY_DRIVER_MIN_COVERAGE = (len(DAILY_DRIVER_CATEGORIES) + 1) // 2
PORTFOLIO_OPTION_COUNT = 2
PORTFOLIO_TIER_ORDER = {"value": 1, "balanced": 2, "premium": 3}
PORTFOLIO_ALLOCATIONS = (
    {
        "key": "specialist",
        "label": "Specialist work",
        "share": 0.10,
        "tier": "premium",
        "description": "Reserve the strongest model for the hardest tasks.",
    },
    {
        "key": "balanced",
        "label": "Everyday work",
        "share": 0.30,
        "tier": "balanced",
        "description": "Use a capable middle tier for routine work.",
    },
    {
        "key": "volume",
        "label": "High-volume work",
        "share": 0.60,
        "tier": "value",
        "description": "Keep the majority of work on the economical tier.",
    },
)

def configuration_id(result: Result) -> str:
    """Return the stable identity for a model plus its runtime settings."""

    identity = result.configuration_id or (
        f"{result.model_id}@{result.effort_level}" if result.effort_level else result.model_id
    )
    return f"{identity}@agent:{result.agent_id}" if result.agent_id else identity


def configuration_label(result: Result) -> str:
    if result.effort_level and result.effort_level.lower() not in result.model_name.lower():
        return f"{result.model_name} ({result.effort_level})"
    return result.model_name


def _profile_url(rows: list[Result]) -> str | None:
    canonical = [row for row in rows if row.source_id == "benchlm"]
    if not canonical:
        return None
    published = sorted({row.source_model_url for row in canonical if row.source_model_url})
    return published[0] if published else model_profile_url(canonical[0].model_id)


def deduplicate_results(results: list[Result]) -> list[Result]:
    """Keep one canonical result per benchmark and evaluated configuration."""

    grouped: dict[tuple[str, str], list[Result]] = defaultdict(list)
    for result in results:
        grouped[(configuration_id(result), result.benchmark_id)].append(result)
    selected: list[Result] = []
    for rows in grouped.values():
        canonical = [row for row in rows if row.source_id == "benchlm"] or rows
        latest_date = max(row.retrieved_date for row in canonical)
        selected.append(min(
            (row for row in canonical if row.retrieved_date == latest_date),
            key=lambda row: (row.source_id, row.evidence_url, json.dumps(row.to_dict(), sort_keys=True)),
        ))
    return sorted(
        selected,
        key=lambda result: (
            result.category,
            result.model_name,
            result.benchmark_id,
            result.effort_level or "",
            result.source_id,
        ),
    )


def load_results(path: Path) -> list[Result]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    catalog = json.loads((Path(__file__).resolve().parents[1] / "catalog/sources.json").read_text(encoding="utf-8"))
    approved = {
        source["id"] for source in catalog["sources"]
        if source["source_status"] == "approved"
        and source.get("redistribution") in {"allowed", "allowed_with_attribution"}
    }
    loaded = [
        result
        for result in (Result.from_dict(record) for record in payload.get("records", []))
        if is_model_in_scope(result.model_name) and result.source_id in approved
    ]
    return deduplicate_results(loaded)


def category_rows(results: list[Result], category: str) -> list[dict[str, Any]]:
    rows = [result for result in deduplicate_results(results) if result.category == category]
    return [
        {
            "model_id": result.model_id,
            "configuration_id": configuration_id(result),
            "model_name": result.model_name,
            "configuration_label": configuration_label(result),
            "provider": result.provider,
            "agent_id": result.agent_id,
            "effort_level": result.effort_level,
            "category": result.category,
            "benchmark_id": result.benchmark_id,
            "benchmark_version": result.benchmark_version,
            "score": result.score,
            "score_unit": result.score_unit,
            "cost_per_task_usd": result.cost_per_task_usd,
            "cost_basis": result.cost_basis,
            "input_price_per_million_usd": result.input_price_per_million_usd,
            "output_price_per_million_usd": result.output_price_per_million_usd,
            "pricing_source_url": result.pricing_source_url,
            "source_id": result.source_id,
            "source_url": result.source_url,
            "evidence_url": result.evidence_url,
            "original_source_url": result.original_source_url,
            "source_license_url": result.source_license_url,
            "retrieved_date": result.retrieved_date,
            "evaluation_type": result.evaluation_type,
            "derivation_type": result.derivation_type,
            "attribution": result.attribution,
            "source_total_cost_usd": result.source_total_cost_usd,
            "source_total_tokens": result.source_total_tokens,
            "source_trial_count": result.source_trial_count,
            "source_task_count": result.source_task_count,
        }
        for result in sorted(rows, key=lambda item: (-item.score, item.model_name))
    ]


def recommendations(
    results: list[Result],
    benchlm_metrics: dict[str, Any] | None = None,
) -> dict[str, dict[str, dict[str, Any] | None]]:
    results = deduplicate_results(results)
    summaries = model_summary_rows(results, benchlm_metrics=benchlm_metrics)
    output: dict[str, dict[str, dict[str, Any] | None]] = {}
    for domain in TOP_LEVEL_DOMAINS:
        domain_rows = [
            summary for summary in _representative_summaries(
                summaries,
                "domain_scores",
                "domain_score_ranges",
                domain,
            )
            if summary["domain_scores"].get(domain) is not None
        ]
        if not domain_rows:
            continue
        quality = max(
            domain_rows,
            key=lambda item: (
                _nested_range_max(item, "domain_score_ranges", domain, item["domain_scores"][domain]),
                item["model_name"],
            ),
        )
        token_priced = [
            item for item in domain_rows
            if item["blended_token_price_per_million_usd"] is not None
        ]
        output[domain] = {
            "best_quality": _compact_summary(quality, domain),
            "cheapest": None,
            "best_value": _compact_summary(
                min(
                    token_priced,
                    key=lambda item: (
                        item["blended_token_price_per_million_usd"]
                        / max(_nested_range_max(item, "domain_score_ranges", domain, item["domain_scores"][domain]), 0.001),
                        -_nested_range_max(item, "domain_score_ranges", domain, item["domain_scores"][domain]),
                        item["model_name"],
                    ),
                ),
                domain,
            ) if token_priced else None,
            "lowest_token_price": _compact_summary(
                min(
                    token_priced,
                    key=lambda item: (
                        item["blended_token_price_per_million_usd"],
                        -_nested_range_max(item, "domain_score_ranges", domain, item["domain_scores"][domain]),
                        item["model_name"],
                    ),
                ),
                domain,
            ) if token_priced else None,
        }

    daily_rows = daily_driver_rows(results, benchlm_metrics=benchlm_metrics)
    if daily_rows:
        daily_candidates = [
            row for row in _representative_daily_rows(daily_rows)
            if row["coverage"] >= DAILY_DRIVER_MIN_COVERAGE
        ] or _representative_daily_rows(daily_rows)
        task_priced_daily = [
            row for row in daily_candidates
            if row["cost_per_task_usd"] is not None
        ]
        token_priced_daily = [
            row for row in daily_candidates
            if row["input_price_per_million_usd"] is not None
            and row["output_price_per_million_usd"] is not None
        ]
        best_value_daily = (
            min(
                task_priced_daily,
                key=lambda item: (
                    item["cost_per_task_usd"] / max(_range_max(item, "daily_driver_score_range", item["score"]), 0.001),
                    -_range_max(item, "daily_driver_score_range", item["score"]),
                    item["model_name"],
                ),
            )
            if task_priced_daily
            else min(
                token_priced_daily,
                key=lambda item: (
                    (item["input_price_per_million_usd"] + item["output_price_per_million_usd"])
                    / max(_range_max(item, "daily_driver_score_range", item["score"]), 0.001),
                    -_range_max(item, "daily_driver_score_range", item["score"]),
                    item["model_name"],
                ),
                default=None,
            )
        )
        output[DAILY_DRIVER_CATEGORY] = {
            "best_quality": min(
                daily_candidates,
                key=lambda item: (
                    -_range_max(item, "daily_driver_score_range", item["score"]),
                    item["model_name"],
                ),
            ),
            "cheapest": min(
                task_priced_daily,
                key=lambda item: (
                    item["cost_per_task_usd"],
                    -_range_max(item, "daily_driver_score_range", item["score"]),
                    item["model_name"],
                ),
                default=None,
            ),
            "best_value": best_value_daily,
            "lowest_token_price": min(
                token_priced_daily,
                key=lambda item: (
                    item["input_price_per_million_usd"] + item["output_price_per_million_usd"],
                    -_range_max(item, "daily_driver_score_range", item["score"]),
                    item["model_name"],
                ),
                default=None,
            ),
        }
    return output


def _benchmark_percentiles(results: list[Result]) -> dict[tuple[str, str], float]:
    benchmark_rows: dict[str, list[Result]] = defaultdict(list)
    for result in results:
        if result.category in DAILY_DRIVER_CATEGORIES:
            benchmark_rows[result.benchmark_id].append(result)

    percentiles: dict[tuple[str, str], float] = {}
    for benchmark_id, rows in benchmark_rows.items():
        count = len(rows)
        for row in rows:
            if count == 1:
                percentile = 50.0
            else:
                lower = sum(other.score < row.score for other in rows)
                equal = sum(other.score == row.score for other in rows)
                mid_rank = lower + (equal + 1) / 2
                percentile = 100 * (mid_rank - 1) / (count - 1)
            percentiles[(configuration_id(row), benchmark_id)] = percentile
    return percentiles


def _category_score_lists(results: list[Result]) -> dict[str, dict[str, list[float]]]:
    percentiles = _benchmark_percentiles(results)
    category_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for result in results:
        if result.category in DAILY_DRIVER_CATEGORIES:
            category_scores[configuration_id(result)][result.category].append(
                percentiles[(configuration_id(result), result.benchmark_id)]
            )
    return category_scores


def _category_score_means(results: list[Result]) -> dict[str, dict[str, float]]:
    return {
        model_id: {
            category: sum(scores) / len(scores)
            for category, scores in categories.items()
        }
        for model_id, categories in _category_score_lists(results).items()
    }


def _domain_score_means(
    normalized_category_scores: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Average normalized subcategory scores into the three work domains."""

    return {
        model_id: {
            domain: sum(category_scores[category] for category in categories if category in category_scores)
            / len([category for category in categories if category in category_scores])
            for domain, categories in DOMAIN_CATEGORIES.items()
            if any(category in category_scores for category in categories)
        }
        for model_id, category_scores in normalized_category_scores.items()
    }


def _domain_coverage(category_scores: dict[str, float]) -> dict[str, int]:
    return {
        domain: sum(category in category_scores for category in categories)
        for domain, categories in DOMAIN_CATEGORIES.items()
    }


def _benchlm_metric_records(benchlm_metrics: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not benchlm_metrics or benchlm_metrics.get("status") != "available":
        return {}
    return {
        record["model_id"]: record
        for record in benchlm_metrics.get("records", [])
        if record.get("model_id")
    }


def _benchlm_domain_signal(
    record: dict[str, Any] | None,
    domain: str,
) -> tuple[float, str, list[str]] | None:
    if not record:
        return None
    benchmarks = record.get("benchmarks", {})
    values = [
        (key, benchmarks.get(key, {}).get("score"))
        for key in BENCHLM_DOMAIN_BENCHMARKS[domain]
        if isinstance(benchmarks.get(key), dict)
        and isinstance(benchmarks[key].get("score"), (int, float))
        and not isinstance(benchmarks[key].get("score"), bool)
    ]
    if values:
        labels = [BENCHLM_BENCHMARK_LABELS[key] for key, _ in values]
        urls = [BENCHLM_BENCHMARK_URLS[key] for key, _ in values]
        return (
            round(sum(value for _, value in values) / len(values), 1),
            f"BenchLM {' + '.join(labels)}",
            urls,
        )
    agentic = record.get("agentic_score")
    if domain in {"engineering", "management"} and isinstance(agentic, (int, float)) and not isinstance(agentic, bool):
        return round(agentic, 1), "BenchLM agentic score (domain proxy)", [BENCHLM_AGENTIC_URL]
    return None


def _effort_sort_key(level: str | None) -> tuple[int, str]:
    order = {"low": 1, "medium": 2, "high": 3, "xhigh": 4, "max": 5}
    normalized = (level or "").lower()
    return (order.get(normalized, 0), normalized)


def _summary_group_key(summary: dict[str, Any]) -> tuple[str, str | None]:
    """Keep named agents separate when comparing effort configurations."""

    return (summary["model_id"], summary.get("agent_id"))


def _range_record(values: list[tuple[float, str]]) -> dict[str, Any] | None:
    if not values:
        return None
    ordered = sorted(values, key=lambda item: (item[0], item[1]))
    return {
        "min": round(ordered[0][0], 1),
        "max": round(ordered[-1][0], 1),
        "configurations": [configuration for _, configuration in ordered],
    }


def _attach_effort_ranges(summaries: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for summary in summaries:
        grouped[_summary_group_key(summary)].append(summary)
    for summary in summaries:
        peers = grouped[_summary_group_key(summary)]
        effort_levels = sorted(
            {peer["effort_level"] for peer in peers if peer.get("effort_level")},
            key=_effort_sort_key,
        )
        summary["effort_levels"] = effort_levels
        summary["effort_configuration_count"] = len(peers)
        summary["score_range_basis"] = "Observed configurations only; no effort interpolation"
        summary["category_score_ranges"] = {
            category: range_record
            for category in DAILY_DRIVER_CATEGORIES
            if (range_record := _range_record([
                (peer["category_scores"][category], peer["configuration_id"])
                for peer in peers
                if category in peer["category_scores"]
            ])) is not None
        }
        summary["domain_score_ranges"] = {
            domain: range_record
            for domain in TOP_LEVEL_DOMAINS
            if (range_record := _range_record([
                (peer["domain_scores"][domain], peer["configuration_id"])
                for peer in peers
                if domain in peer["domain_scores"]
            ])) is not None
        }
        summary["daily_driver_score_range"] = _range_record([
            (peer["daily_driver_score"], peer["configuration_id"])
            for peer in peers
            if peer["daily_driver_score"] is not None
        ])


def _range_max(summary: dict[str, Any], field: str, fallback: float | None = None) -> float | None:
    record = summary.get(field)
    if isinstance(record, dict) and record.get("max") is not None:
        return float(record["max"])
    return fallback


def _nested_range_max(
    summary: dict[str, Any],
    field: str,
    key: str,
    fallback: float | None = None,
) -> float | None:
    record = summary.get(field, {}).get(key)
    if isinstance(record, dict) and record.get("max") is not None:
        return float(record["max"])
    return fallback


def _representative_summaries(
    summaries: list[dict[str, Any]],
    score_field: str,
    score_range_field: str,
    score_key: str | None = None,
) -> list[dict[str, Any]]:
    """Select the strongest observed effort configuration per model/agent."""

    grouped: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for summary in summaries:
        grouped[_summary_group_key(summary)].append(summary)

    def score_value(item: dict[str, Any]) -> float | None:
        value = item.get(score_field)
        if score_key:
            value = value.get(score_key) if isinstance(value, dict) else None
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    representatives = []
    for peers in grouped.values():
        representatives.append(max(
            peers,
            key=lambda item: (
                (
                    _nested_range_max(item, score_range_field, score_key, score_value(item))
                    if score_key
                    else _range_max(item, score_range_field, score_value(item))
                ) or -1,
                score_value(item) or -1,
                len(item.get("evidence", [])),
                item.get("configuration_id", ""),
            ),
        ))
    return sorted(representatives, key=lambda item: (item["model_name"], item["configuration_id"]))


def _representative_daily_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("base_model_id", row["model_id"]), row.get("agent_id"))].append(row)
    representatives = []
    for peers in grouped.values():
        representatives.append(max(
            peers,
            key=lambda item: (
                _range_max(item, "daily_driver_score_range", item.get("score")) or -1,
                item.get("score") if item.get("score") is not None else -1,
                len(item.get("evidence", [])),
                item.get("configuration_id", ""),
            ),
        ))
    return sorted(representatives, key=lambda item: (item["model_name"], item["configuration_id"]))


def _reported_category_score_means(results: list[Result]) -> dict[str, dict[str, float]]:
    category_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for result in results:
        if result.category in DAILY_DRIVER_CATEGORIES:
            category_scores[configuration_id(result)][result.category].append(result.score)
    return {
        model_id: {
            category: sum(scores) / len(scores)
            for category, scores in categories.items()
        }
        for model_id, categories in category_scores.items()
    }


def _daily_driver_score(category_scores: dict[str, float]) -> float | None:
    if not category_scores:
        return None
    quality = sum(category_scores.values()) / len(category_scores)
    coverage = len(category_scores)
    return round(0.75 * quality + 25 * coverage / len(DAILY_DRIVER_CATEGORIES), 1)


def _benchlm_daily_signal(record: dict[str, Any] | None) -> tuple[float, str, str] | None:
    """Return the strongest source-owned cross-work signal available."""

    if not record:
        return None
    agentic = record.get("agentic_score")
    if isinstance(agentic, (int, float)) and not isinstance(agentic, bool):
        return round(agentic, 1), "BenchLM agentic score", BENCHLM_AGENTIC_URL
    overall = record.get("overall_score")
    if isinstance(overall, (int, float)) and not isinstance(overall, bool):
        return round(overall, 1), "BenchLM overall score (agentic unavailable)", BENCHLM_OVERALL_URL
    return None


def daily_driver_rows(
    results: list[Result],
    benchlm_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build transparent daily-driver rows for the dashboard.

    BenchLM's published agentic score is used directly when available. When
    BenchLM has no agentic score, its published overall score is used as an
    explicitly labeled fallback. Models without either source value retain the
    deterministic local fallback: scores are normalized within each benchmark
    using a mid-rank percentile, then combined with a 25% coverage component
    across the eight work categories. A one-model benchmark is assigned a
    neutral 50 percentile.
    """

    results = deduplicate_results(results)
    metric_by_model = _benchlm_metric_records(benchlm_metrics)
    category_scores = _category_score_lists(results)
    model_rows: dict[str, list[Result]] = defaultdict(list)
    for result in results:
        if result.category not in DAILY_DRIVER_CATEGORIES:
            continue
        model_rows[configuration_id(result)].append(result)

    output: list[dict[str, Any]] = []
    for model_id, categories in sorted(category_scores.items()):
        category_means = {
            category: sum(scores) / len(scores)
            for category, scores in categories.items()
        }
        coverage = len(category_means)
        rows = model_rows[model_id]
        source_metric = metric_by_model.get(rows[0].model_id)
        source_signal = _benchlm_daily_signal(source_metric)
        if source_signal:
            index, score_basis, score_source_url = source_signal
        else:
            index = _daily_driver_score(category_means)
            score_basis = "modelagency derived percentile + coverage"
            score_source_url = "https://github.com/aknochow/modelagency#daily-driver-index"
        price_row = min(
            (row for row in rows if row.input_price_per_million_usd is not None and row.output_price_per_million_usd is not None),
            key=lambda row: (
                row.input_price_per_million_usd + row.output_price_per_million_usd,
                row.model_name,
            ),
            default=None,
        )
        first = rows[0]
        retrieved_date = max(row.retrieved_date for row in rows)
        output.append({
            "model_id": f"{model_id}:daily-driver",
            "base_model_id": first.model_id,
            "configuration_id": model_id,
            "model_name": first.model_name,
            "configuration_label": configuration_label(first),
            "profile_url": _profile_url(rows),
            "provider": first.provider,
            "agent_id": first.agent_id,
            "effort_level": first.effort_level,
            "category": DAILY_DRIVER_CATEGORY,
            "benchmark_id": DAILY_DRIVER_BENCHMARK_ID,
            "benchmark_version": DAILY_DRIVER_VERSION,
            "score": index,
            "score_unit": "BenchLM source score / 100" if score_basis.startswith("BenchLM") else "derived index / 100",
            "cost_per_task_usd": None,
            "cost_basis": "No task-level usage data in the current sources",
            "input_price_per_million_usd": price_row.input_price_per_million_usd if price_row else None,
            "output_price_per_million_usd": price_row.output_price_per_million_usd if price_row else None,
            "pricing_source_url": price_row.pricing_source_url if price_row else None,
            "source_id": "modelagency-derived",
            "source_url": "https://github.com/aknochow/modelagency",
            "evidence_url": "https://github.com/aknochow/modelagency#daily-driver-index",
            "original_source_url": None,
            "source_license_url": "https://github.com/aknochow/modelagency/blob/main/LICENSE",
            "retrieved_date": retrieved_date,
            "evaluation_type": "derived",
            "derivation_type": "derived",
            "attribution": "Derived by modelagency from the linked benchmark records; see the daily-driver methodology.",
            "coverage": coverage,
            "coverage_total": len(DAILY_DRIVER_CATEGORIES),
            "category_scores": category_means,
            "score_basis": score_basis,
            "score_source_url": score_source_url,
        })
    grouped: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for row in output:
        grouped[(row["base_model_id"], row.get("agent_id"))].append(row)
    for row in output:
        peers = grouped[(row["base_model_id"], row.get("agent_id"))]
        row["effort_levels"] = sorted(
            {peer["effort_level"] for peer in peers if peer.get("effort_level")},
            key=_effort_sort_key,
        )
        row["effort_configuration_count"] = len(peers)
        row["score_range_basis"] = "Observed configurations only; no effort interpolation"
        row["daily_driver_score_range"] = _range_record([
            (peer["score"], peer["configuration_id"])
            for peer in peers
        ])
    return sorted(output, key=lambda row: (row["category"], row["model_name"], row["configuration_id"]))


def model_summary_rows(
    results: list[Result],
    benchlm_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build one sortable, provenance-linked row per tracked model.

    Raw category values remain means of the linked benchmark scores in their
    native published units. Source-backed domain values use the matching
    BenchLM lanes when available; local percentile normalization remains the
    explicit fallback. Cost tiers are relative token-price proxies, not task
    costs.
    """

    results = deduplicate_results(results)
    metric_by_model = _benchlm_metric_records(benchlm_metrics)
    normalized_category_scores = _category_score_means(results)
    reported_category_scores = _reported_category_score_means(results)
    model_rows: dict[str, list[Result]] = defaultdict(list)
    for result in results:
        model_rows[configuration_id(result)].append(result)

    summaries: list[dict[str, Any]] = []
    for model_id, rows in sorted(model_rows.items()):
        first = rows[0]
        normalized_scores = normalized_category_scores.get(model_id, {})
        reported_scores = reported_category_scores.get(model_id, {})
        domain_scores = _domain_score_means({model_id: normalized_scores}).get(model_id, {})
        domain_score_bases = {
            domain: "modelagency derived percentile index"
            for domain in domain_scores
        }
        domain_score_source_urls = {
            domain: []
            for domain in domain_scores
        }
        metric_record = metric_by_model.get(first.model_id)
        for domain in TOP_LEVEL_DOMAINS:
            signal = _benchlm_domain_signal(metric_record, domain)
            if signal is None:
                continue
            source_score, source_basis, source_urls = signal
            domain_scores[domain] = source_score
            domain_score_bases[domain] = source_basis
            domain_score_source_urls[domain] = source_urls
        source_signal = _benchlm_daily_signal(metric_record)
        if source_signal:
            daily_driver_score, daily_driver_score_basis, daily_driver_score_source_url = source_signal
        else:
            daily_driver_score = _daily_driver_score(normalized_scores)
            daily_driver_score_basis = "modelagency derived percentile + coverage"
            daily_driver_score_source_url = "https://github.com/aknochow/modelagency#daily-driver-index"
        domain_coverage = _domain_coverage(normalized_scores)
        scores = {category: round(score, 1) for category, score in reported_scores.items()}
        units = {
            category: sorted({row.score_unit for row in rows if row.category == category})
            for category in reported_scores
        }
        price_row = min(
            (row for row in rows if row.input_price_per_million_usd is not None and row.output_price_per_million_usd is not None),
            key=lambda row: (
                row.input_price_per_million_usd + row.output_price_per_million_usd,
                row.model_name,
            ),
            default=None,
        )
        evidence = [
            _evidence_record(row)
            for row in sorted(rows, key=lambda item: (item.category, item.benchmark_id, item.evidence_url))
        ]
        blended_price = (
            price_row.input_price_per_million_usd + price_row.output_price_per_million_usd
            if price_row else None
        )
        summaries.append({
            "model_id": first.model_id,
            "configuration_id": model_id,
            "model_name": first.model_name,
            "configuration_label": configuration_label(first),
            "profile_url": _profile_url(rows),
            "provider": first.provider,
            "agent_id": first.agent_id,
            "effort_level": first.effort_level,
            "category_scores": scores,
            "category_units": units,
            "domain_scores": {domain: round(score, 1) for domain, score in domain_scores.items()},
            "domain_score_bases": domain_score_bases,
            "domain_score_source_urls": domain_score_source_urls,
            "domain_coverage": domain_coverage,
            "domain_coverage_total": {
                domain: len(categories)
                for domain, categories in DOMAIN_CATEGORIES.items()
            },
            "daily_driver_score": daily_driver_score,
            "daily_driver_score_basis": daily_driver_score_basis,
            "daily_driver_score_source_url": daily_driver_score_source_url,
            "coverage": len(scores),
            "coverage_total": len(DAILY_DRIVER_CATEGORIES),
            "input_price_per_million_usd": price_row.input_price_per_million_usd if price_row else None,
            "output_price_per_million_usd": price_row.output_price_per_million_usd if price_row else None,
            "blended_token_price_per_million_usd": blended_price,
            "cost_tier": None,
            "cost_tier_label": None,
            "cost_basis": "Blended input + output token price per 1M; proxy, not task cost",
            "source_ids": sorted({row.source_id for row in rows}),
            "pricing_source_url": price_row.pricing_source_url if price_row else None,
            "evidence": evidence,
        })

    _attach_effort_ranges(summaries)

    prices = sorted({
        row["blended_token_price_per_million_usd"]
        for row in summaries
        if row["blended_token_price_per_million_usd"] is not None
    })
    price_tiers = {
        price: 1 if len(prices) == 1 else 1 + int(index * 4 / (len(prices) - 1))
        for index, price in enumerate(prices)
    }
    for row in summaries:
        tier = price_tiers.get(row["blended_token_price_per_million_usd"])
        row["cost_tier"] = tier
        row["cost_tier_label"] = "$" * tier if tier else None
    return summaries


def _monthly_cost(
    summary: dict[str, Any],
    monthly_input_tokens: int,
    monthly_output_tokens: int,
) -> float | None:
    input_price = summary.get("input_price_per_million_usd")
    output_price = summary.get("output_price_per_million_usd")
    if not isinstance(input_price, (int, float)) or isinstance(input_price, bool):
        return None
    if not isinstance(output_price, (int, float)) or isinstance(output_price, bool):
        return None
    if input_price < 0 or output_price < 0:
        return None
    return (
        monthly_input_tokens / 1_000_000 * input_price
        + monthly_output_tokens / 1_000_000 * output_price
    )


def _portfolio_tier(summary: dict[str, Any]) -> str | None:
    tier = summary.get("cost_tier")
    if not isinstance(tier, int):
        return None
    if tier >= 4:
        return "premium"
    if tier in {2, 3}:
        return "balanced"
    return "value"


def _portfolio_option_sort_key(candidate: tuple[dict[str, Any], float, str, float, str], target_tier: str) -> tuple[int, float, float, str]:
    summary, cost, tier, quality, _ = candidate
    tier_distance = abs(PORTFOLIO_TIER_ORDER[tier] - PORTFOLIO_TIER_ORDER[target_tier])
    return (tier_distance, -quality, cost, summary["configuration_id"])


def portfolio_recommendations(
    summaries: list[dict[str, Any]],
    *,
    monthly_budget_usd: int = 300,
    monthly_input_tokens: int = 20_000_000,
    monthly_output_tokens: int = 5_000_000,
    benchlm_metrics: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Recommend a deterministic workload mix across three price tiers.

    The percentages describe workload share, not a promise to spend that
    percentage of the budget. Each candidate is evaluated using the full
    workload token assumptions before its share is applied.
    """

    representatives = _representative_summaries(
        summaries,
        "daily_driver_score",
        "daily_driver_score_range",
    )
    metric_by_model = {
        record.get("model_id"): record
        for record in (benchlm_metrics or {}).get("records", [])
        if record.get("model_id")
    }
    candidates = []
    for summary in representatives:
        cost = _monthly_cost(summary, monthly_input_tokens, monthly_output_tokens)
        tier = _portfolio_tier(summary)
        source_metric = metric_by_model.get(summary["model_id"], {})
        overall_quality = source_metric.get("overall_score")
        agentic_quality = source_metric.get("agentic_score")
        if isinstance(overall_quality, (int, float)) and not isinstance(overall_quality, bool):
            quality = round(overall_quality, 1)
            quality_source = "BenchLM overall score"
        elif isinstance(agentic_quality, (int, float)) and not isinstance(agentic_quality, bool):
            quality = round(agentic_quality, 1)
            quality_source = "BenchLM agentic score"
        else:
            quality = _range_max(
                summary, "daily_driver_score_range", summary.get("daily_driver_score")
            )
            quality_source = "modelagency derived Daily Driver range"
        if cost is None or tier is None or quality is None:
            continue
        candidates.append((summary, cost, tier, quality, quality_source))
    if not candidates:
        return None

    by_tier = {
        tier: [candidate for candidate in candidates if candidate[2] == tier]
        for tier in {allocation["tier"] for allocation in PORTFOLIO_ALLOCATIONS}
    }
    all_candidates = candidates
    pools = [by_tier[allocation["tier"]] or all_candidates for allocation in PORTFOLIO_ALLOCATIONS]
    unlimited = monthly_budget_usd >= 5_000
    def choose(allow_reuse: bool):
        best: tuple[float, float, int, tuple[str, ...], tuple[tuple[dict[str, Any], float, str, float, str], ...]] | None = None
        for combination in product(*pools):
            identifiers = tuple(candidate[0]["configuration_id"] for candidate in combination)
            if not allow_reuse and len(set(identifiers)) < len(identifiers) and len(candidates) >= len(combination):
                continue
            total_cost = sum(
                allocation["share"] * candidate[1]
                for allocation, candidate in zip(PORTFOLIO_ALLOCATIONS, combination)
            )
            if not unlimited and total_cost > monthly_budget_usd:
                continue
            weighted_quality = sum(
                allocation["share"] * candidate[3]
                for allocation, candidate in zip(PORTFOLIO_ALLOCATIONS, combination)
            )
            distinct_count = len(set(identifiers))
            ranking = (weighted_quality, -total_cost, distinct_count, tuple(identifiers))
            if best is None or ranking > best[:4]:
                best = (*ranking, combination)
        return best

    best = choose(False) or choose(True)
    if best is None:
        return None

    combination = best[4]
    reused_model = len({candidate[0]["configuration_id"] for candidate in combination}) < len(combination)
    allocations = []
    for index, (allocation, candidate) in enumerate(zip(PORTFOLIO_ALLOCATIONS, combination)):
        summary, full_cost, tier, quality, quality_source = candidate
        option_pool = list(by_tier[allocation["tier"]])
        if not option_pool:
            option_pool = list(all_candidates)
        option_pool.sort(key=lambda item: _portfolio_option_sort_key(item, allocation["tier"]))
        if len(option_pool) < PORTFOLIO_OPTION_COUNT:
            nearby = sorted(
                (item for item in all_candidates if item not in option_pool),
                key=lambda item: _portfolio_option_sort_key(item, allocation["tier"]),
            )
            option_pool.extend(nearby[: PORTFOLIO_OPTION_COUNT - len(option_pool)])
        selected_id = summary["configuration_id"]
        option_pool = [candidate] + [
            item for item in option_pool if item[0]["configuration_id"] != selected_id
        ][: PORTFOLIO_OPTION_COUNT - 1]
        options = []
        for option in option_pool:
            option_summary, option_cost, option_tier, option_quality, option_quality_source = option
            option_total = sum(
                item_allocation["share"] * (option_cost if item_index == index else other_candidate[1])
                for item_index, (item_allocation, other_candidate) in enumerate(
                    zip(PORTFOLIO_ALLOCATIONS, combination)
                )
            )
            options.append({
                "configuration_id": option_summary["configuration_id"],
                "configuration_label": option_summary["configuration_label"],
                "effort_level": option_summary.get("effort_level"),
                "full_workload_cost": round(option_cost, 4),
                "allocated_monthly_cost": round(option_cost * allocation["share"], 4),
                "fits_budget": unlimited or option_total <= monthly_budget_usd,
                "mix_monthly_cost": round(option_total, 4),
                "model_id": option_summary["model_id"],
                "model_name": option_summary["model_name"],
                "quality_range": (
                    option_summary.get("daily_driver_score_range")
                    if not option_quality_source.startswith("BenchLM")
                    else None
                ),
                "quality_score": round(option_quality, 1),
                "quality_source": option_quality_source,
                "selected": option_summary["configuration_id"] == selected_id,
                "tier": option_tier,
            })
        allocations.append({
            "key": allocation["key"],
            "label": allocation["label"],
            "description": allocation["description"],
            "share": allocation["share"],
            "share_percent": int(allocation["share"] * 100),
            "tier": tier,
            "model_id": summary["model_id"],
            "configuration_id": summary["configuration_id"],
            "model_name": summary["model_name"],
            "configuration_label": summary["configuration_label"],
            "effort_level": summary.get("effort_level"),
            "quality_score": round(quality, 1),
            "quality_source": quality_source,
            "quality_range": (
                summary.get("daily_driver_score_range")
                if not quality_source.startswith("BenchLM")
                else None
            ),
            "full_workload_cost": round(full_cost, 4),
            "allocated_monthly_cost": round(full_cost * allocation["share"], 4),
            "options": options,
        })
    total_cost = sum(item["allocated_monthly_cost"] for item in allocations)
    return {
        "budget_usd": monthly_budget_usd,
        "monthly_input_tokens": monthly_input_tokens,
        "monthly_output_tokens": monthly_output_tokens,
        "workload_share_total": 1.0,
        "estimated_monthly_cost": round(total_cost, 4),
        "remaining_budget": None if unlimited else round(monthly_budget_usd - total_cost, 4),
        "selection_basis": (
            "10% specialist, 30% balanced, and 60% value workload shares; "
            "BenchLM overall scores lead for workload mix quality, with agentic scores and observed effort maximums as fallbacks; "
            "each tier includes the selected budget-fit model and a score-ranked alternative when available"
            + ("; a selected model is reused because no distinct mix fits the budget" if reused_model else "")
        ),
        "reused_model": reused_model,
        "allocations": allocations,
    }


def _compact_summary(summary: dict[str, Any], domain: str) -> dict[str, Any]:
    """Expose a domain recommendation with links to its underlying evidence."""

    categories = set(DOMAIN_CATEGORIES[domain])
    evidence = [entry for entry in summary["evidence"] if entry["category"] in categories]
    first_evidence = evidence[0] if evidence else {}
    return {
        "model_id": summary["model_id"],
        "configuration_id": summary["configuration_id"],
        "model_name": summary["model_name"],
        "configuration_label": summary["configuration_label"],
        "profile_url": summary["profile_url"],
        "provider": summary["provider"],
        "agent_id": summary["agent_id"],
        "effort_level": summary["effort_level"],
        "category": domain,
        "score": summary["domain_scores"][domain],
        "score_unit": "BenchLM source score / 100" if summary.get("domain_score_bases", {}).get(domain, "").startswith("BenchLM") else "derived index / 100",
        "score_range": summary["domain_score_ranges"].get(domain),
        "score_range_basis": summary["score_range_basis"],
        "score_basis": summary.get("domain_score_bases", {}).get(domain),
        "score_source_urls": summary.get("domain_score_source_urls", {}).get(domain, []),
        "effort_levels": summary["effort_levels"],
        "cost_per_task_usd": None,
        "input_price_per_million_usd": summary["input_price_per_million_usd"],
        "output_price_per_million_usd": summary["output_price_per_million_usd"],
        "pricing_source_url": summary["pricing_source_url"],
        "source_id": ", ".join(summary["source_ids"]),
        "evidence_url": first_evidence.get("evidence_url"),
        "original_source_url": first_evidence.get("original_source_url"),
        "attribution": "Derived from normalized subcategory scores; see linked benchmark evidence.",
        "coverage": summary["domain_coverage"][domain],
        "coverage_total": summary["domain_coverage_total"][domain],
        "evidence": evidence,
    }


def _compact(result: Result) -> dict[str, Any]:
    return {
        "model_id": result.model_id,
        "configuration_id": configuration_id(result),
        "model_name": result.model_name,
        "configuration_label": configuration_label(result),
        "provider": result.provider,
        "agent_id": result.agent_id,
        "effort_level": result.effort_level,
        "category": result.category,
        "benchmark_id": result.benchmark_id,
        "score": result.score,
        "score_unit": result.score_unit,
        "score_range": result.get("daily_driver_score_range") if isinstance(result, dict) else None,
        "score_range_basis": result.get("score_range_basis") if isinstance(result, dict) else None,
        "effort_levels": result.get("effort_levels", []) if isinstance(result, dict) else [],
        "cost_per_task_usd": result.cost_per_task_usd,
        "input_price_per_million_usd": result.input_price_per_million_usd,
        "output_price_per_million_usd": result.output_price_per_million_usd,
        "pricing_source_url": result.pricing_source_url,
        "source_id": result.source_id,
        "evidence_url": result.evidence_url,
        "original_source_url": result.original_source_url,
        "attribution": result.attribution,
    }


def _evidence_record(result: Result) -> dict[str, Any]:
    record = {
        "category": result.category,
        "benchmark_id": result.benchmark_id,
        "benchmark_version": result.benchmark_version,
        "score": result.score,
        "score_unit": result.score_unit,
        "source_id": result.source_id,
        "evidence_url": result.evidence_url,
        "original_source_url": result.original_source_url,
        "attribution": result.attribution,
    }
    for field in (
        "retrieved_date",
        "source_generated_at",
        "source_license_url",
        "evaluation_type",
        "derivation_type",
        "source_total_cost_usd",
        "source_total_tokens",
        "source_trial_count",
        "source_task_count",
    ):
        value = getattr(result, field)
        if value is not None:
            record[field] = value
    return record
