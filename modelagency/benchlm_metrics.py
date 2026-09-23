"""Validation for the small source-owned BenchLM metrics snapshot.

The snapshot keeps the values needed by the dashboard separate from
modelagency-derived work indexes.  Missing source values stay ``null``.
"""

from __future__ import annotations

import json
from datetime import date
from math import isfinite
from pathlib import Path
from urllib.parse import urlparse

SOURCE_URL = "https://benchlm.ai/"
AGENTIC_URL = "https://benchlm.ai/llm-agent-benchmarks"
LICENSE_URL = "https://benchlm.ai/data"
BENCHMARK_URLS = {
    "terminal_bench_2": "https://benchlm.ai/benchmarks/terminal-bench-2",
    "browsecomp": "https://benchlm.ai/benchmarks/browsecomp",
    "osworld_verified": "https://benchlm.ai/benchmarks/osworld-verified",
}


def _is_benchlm_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.netloc == "benchlm.ai"


def _number_or_none(value: object, field: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{field} must be a finite number or null")


def _positive_int_or_none(value: object, field: str) -> None:
    if value is None:
        return
    if type(value) is not int or value < 1:
        raise ValueError(f"{field} must be a positive integer or null")


def _metric_record(record: dict) -> None:
    for field in ("model_id", "model_name", "provider", "profile_url"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"BenchLM metrics requires {field}")
    if not _is_benchlm_url(record["profile_url"]):
        raise ValueError("BenchLM metrics profile_url must be a BenchLM URL")

    for field in ("agentic_score", "overall_score"):
        _number_or_none(record.get(field), field)
    for field in ("agentic_rank", "overall_rank"):
        _positive_int_or_none(record.get(field), field)
    for field in ("agentic_status", "overall_status"):
        value = record.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{field} must be a non-empty string or null")

    benchmarks = record.get("benchmarks")
    if not isinstance(benchmarks, dict):
        raise ValueError("BenchLM metrics requires a benchmarks object")
    for key, expected_url in BENCHMARK_URLS.items():
        metric = benchmarks.get(key)
        if not isinstance(metric, dict):
            raise ValueError(f"BenchLM metrics requires benchmark {key}")
        _number_or_none(metric.get("score"), f"benchmarks.{key}.score")
        if metric.get("evidence_url") != expected_url:
            raise ValueError(f"benchmarks.{key}.evidence_url must identify the published page")


def load_metrics(path: Path) -> dict:
    """Load and validate the checked-in, offline BenchLM metrics snapshot."""

    if not path.exists():
        return {"source_id": "benchlm", "source_url": SOURCE_URL, "status": "unavailable", "records": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1" or payload.get("source_id") != "benchlm":
        raise ValueError("BenchLM metrics must use schema v1")
    if payload.get("source_url") != SOURCE_URL or payload.get("agentic_url") != AGENTIC_URL:
        raise ValueError("BenchLM metrics must identify the published leaderboard pages")
    if payload.get("source_license_url") != LICENSE_URL:
        raise ValueError("BenchLM metrics must retain the BenchLM license URL")
    date.fromisoformat(payload["retrieved_date"])
    date.fromisoformat(payload["source_verified_date"])
    if not isinstance(payload.get("attribution"), str) or not payload["attribution"].strip():
        raise ValueError("BenchLM metrics attribution is required")

    seen: set[str] = set()
    for record in payload.get("records", []):
        _metric_record(record)
        if record["model_id"] in seen:
            raise ValueError("duplicate model in BenchLM metrics")
        seen.add(record["model_id"])
    return {**payload, "status": "available" if payload.get("records") else "unavailable"}
