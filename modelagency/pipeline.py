"""Deterministic offline build and recommendation functions."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .schema import Result


def load_results(path: Path) -> list[Result]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Result.from_dict(record) for record in payload.get("records", [])]


def category_rows(results: list[Result], category: str) -> list[dict[str, Any]]:
    rows = [result for result in results if result.category == category]
    return [
        {
            "model_id": result.model_id,
            "model_name": result.model_name,
            "provider": result.provider,
            "agent_id": result.agent_id,
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
        }
        for result in sorted(rows, key=lambda item: (-item.score, item.model_name))
    ]


def recommendations(results: list[Result]) -> dict[str, dict[str, dict[str, Any] | None]]:
    grouped: dict[str, list[Result]] = defaultdict(list)
    for result in results:
        grouped[result.category].append(result)
    output: dict[str, dict[str, dict[str, Any] | None]] = {}
    for category, rows in grouped.items():
        quality = max(rows, key=lambda item: (item.score, item.model_name))
        priced = [item for item in rows if item.cost_per_task_usd is not None]
        output[category] = {
            "best_quality": _compact(quality),
            "cheapest": _compact(min(priced, key=lambda item: (item.cost_per_task_usd, -item.score, item.model_name))) if priced else None,
            "best_value": _compact(min(priced, key=lambda item: (item.cost_per_task_usd / max(item.score, 0.001), -item.score, item.model_name))) if priced else None,
        }
    return output


def _compact(result: Result) -> dict[str, Any]:
    return {
        "model_id": result.model_id,
        "model_name": result.model_name,
        "provider": result.provider,
        "agent_id": result.agent_id,
        "category": result.category,
        "benchmark_id": result.benchmark_id,
        "score": result.score,
        "score_unit": result.score_unit,
        "cost_per_task_usd": result.cost_per_task_usd,
        "input_price_per_million_usd": result.input_price_per_million_usd,
        "output_price_per_million_usd": result.output_price_per_million_usd,
        "pricing_source_url": result.pricing_source_url,
        "source_id": result.source_id,
        "evidence_url": result.evidence_url,
        "original_source_url": result.original_source_url,
        "attribution": result.attribution,
    }
