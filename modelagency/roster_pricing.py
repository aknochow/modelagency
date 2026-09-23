"""Validation for prices attached to roster-only models.

These records intentionally remain separate from benchmark results: a public
token price is useful for budgeting even when the source has not published
benchmark evidence for the model yet.
"""

from __future__ import annotations

import json
from datetime import date
from math import isfinite
from pathlib import Path
from urllib.parse import urlparse

SOURCE_ID = "benchlm"
SOURCE_URL = "https://benchlm.ai/data/models.json"
LICENSE_URL = "https://benchlm.ai/data"


def _is_https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _is_benchlm_url(value: object) -> bool:
    if not _is_https_url(value):
        return False
    return urlparse(value).netloc == "benchlm.ai"


def _price(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise ValueError(f"{field} must be a non-negative finite number")


def _record(record: object) -> None:
    if not isinstance(record, dict):
        raise ValueError("roster pricing records must be objects")
    for field in ("model_id", "model_name", "provider", "profile_url", "pricing_source_url", "pricing_variant"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"roster pricing requires {field}")
    if not _is_benchlm_url(record["profile_url"]):
        raise ValueError("roster pricing profile_url must be a BenchLM URL")
    if not _is_https_url(record["pricing_source_url"]):
        raise ValueError("roster pricing pricing_source_url must be HTTPS")
    for field in ("input_price_per_million_usd", "output_price_per_million_usd"):
        _price(record.get(field), field)
    if "retrieved_date" in record:
        date.fromisoformat(record["retrieved_date"])
    if "notes" in record and (not isinstance(record["notes"], str) or not record["notes"].strip()):
        raise ValueError("roster pricing notes must be a non-empty string when present")


def load_roster_pricing(path: Path) -> dict:
    """Load and validate an offline snapshot of roster-model token prices."""

    if not path.exists():
        return {"schema_version": "1", "source_id": SOURCE_ID, "source_url": SOURCE_URL, "status": "unavailable", "records": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1" or payload.get("source_id") != SOURCE_ID:
        raise ValueError("roster pricing must use schema v1 and the BenchLM source")
    if payload.get("source_url") != SOURCE_URL or payload.get("source_license_url") != LICENSE_URL:
        raise ValueError("roster pricing must identify the BenchLM data and license pages")
    date.fromisoformat(payload["retrieved_date"])
    if not isinstance(payload.get("attribution"), str) or not payload["attribution"].strip():
        raise ValueError("roster pricing attribution is required")

    seen: set[str] = set()
    for record in payload.get("records", []):
        _record(record)
        if record["model_id"] in seen:
            raise ValueError("duplicate model in roster pricing")
        seen.add(record["model_id"])
    return {**payload, "status": "available" if payload.get("records") else "unavailable"}
