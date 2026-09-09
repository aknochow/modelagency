"""BenchLM machine-readable adapter.

Only the explicitly selected BenchLM fields are copied. Artificial Analysis
derived fields are excluded because their separate terms restrict reuse in a
public competitive product. The original benchmark URL is retained alongside
the BenchLM dataset attribution.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from ..schema import Result


MODELS_URL = "https://benchlm.ai/data/models.json"
BENCHMARKS_URL = "https://benchlm.ai/data/benchmarks.json"
PRICING_URL = "https://benchlm.ai/data/pricing.json"
MAX_RESPONSE_BYTES = 25_000_000


def fetch_json(url: str) -> dict[str, Any]:
    if url not in {MODELS_URL, BENCHMARKS_URL, PRICING_URL}:
        raise ValueError(f"URL is not in the BenchLM allowlist: {url}")
    request = Request(url, headers={"User-Agent": "modelagency/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is allowlisted above.
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(f"BenchLM response exceeded {MAX_RESPONSE_BYTES} bytes")
    return json.loads(body)


def load_catalog(root: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads((root / "catalog/benchmarks.json").read_text(encoding="utf-8"))
    return {item["id"]: item for item in payload["benchmarks"]}


def tracked_model(item: dict[str, Any]) -> bool:
    slug = str(item.get("slug", "")).lower()
    return (
        "claude" in slug
        or slug.startswith(("gpt-5-6", "gpt-5.6"))
        or "grok-4-6" in slug
        or "grok-4.6" in slug
        or any(token in slug for token in ("gemini-3-6", "gemini-3.6", "gemini-3-7", "gemini-3.7", "gemini-3-8", "gemini-3.8"))
    )


def is_artificial_analysis_metric(key: str, metadata: dict[str, Any]) -> bool:
    paper_url = str(metadata.get("paperUrl", "")).lower()
    authors = str(metadata.get("authors", "")).lower()
    return key.lower().startswith("aa") or "artificialanalysis.ai" in paper_url or "artificial analysis" in authors


def _scores_by_key(model: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for group in model.get("benchmarks", {}).values():
        if not isinstance(group, dict):
            continue
        for key, value in group.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                scores[key] = float(value)
    return scores


def normalize_payload(
    models_payload: dict[str, Any],
    benchmarks_payload: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    pricing_payload: dict[str, Any] | None = None,
    *,
    retrieved_date: str | None = None,
) -> list[Result]:
    metadata_by_key = {item["benchmarkKey"]: item for item in benchmarks_payload.get("items", [])}
    pricing_by_key = {item["canonicalModelKey"]: item for item in (pricing_payload or {}).get("items", [])}
    retrieved = retrieved_date or str(models_payload.get("generatedAt", date.today().isoformat()))[:10]
    results: list[Result] = []
    for model in models_payload.get("items", []):
        if not tracked_model(model):
            continue
        scores = _scores_by_key(model)
        for benchmark_id, policy in catalog.items():
            metadata = metadata_by_key.get(benchmark_id)
            if not metadata or not policy.get("publish") or benchmark_id not in scores:
                continue
            if is_artificial_analysis_metric(benchmark_id, metadata):
                continue
            evidence_url = metadata.get("url") or model.get("url")
            original_url = metadata.get("paperUrl")
            if not evidence_url or not original_url:
                continue
            attribution = (
                f"Source: BenchLM.ai (https://benchlm.ai), retrieved {retrieved}; "
                f"original benchmark: {metadata.get('authors', 'unspecified')} ({original_url})."
            )
            pricing = pricing_by_key.get(model["canonicalModelKey"], {})
            results.append(Result(
                model_id=model["canonicalModelKey"],
                model_name=model["model"],
                provider=model.get("creator", "Unknown"),
                agent_id=None,
                category=policy["category"],
                benchmark_id=benchmark_id,
                benchmark_version=str(metadata.get("year") or "unspecified"),
                score=scores[benchmark_id],
                score_unit=metadata.get("format", "reported score"),
                cost_per_task_usd=None,
                cost_basis=None,
                input_price_per_million_usd=pricing.get("inputPrice"),
                output_price_per_million_usd=pricing.get("outputPrice"),
                pricing_source_url="https://benchlm.ai/data/pricing.json" if pricing else None,
                source_id="benchlm",
                source_url=MODELS_URL,
                evidence_url=evidence_url,
                original_source_url=original_url,
                source_license_url="https://benchlm.ai/data",
                retrieved_date=retrieved,
                evaluation_type="reported",
                derivation_type="copied_fact",
                attribution=attribution,
            ))
    return sorted(results, key=lambda result: (result.category, result.model_name, result.benchmark_id))


def fetch_results(root: Path) -> list[Result]:
    return normalize_payload(fetch_json(MODELS_URL), fetch_json(BENCHMARKS_URL), load_catalog(root), fetch_json(PRICING_URL))
