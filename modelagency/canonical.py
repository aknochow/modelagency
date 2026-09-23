"""Local contract for source-owned BenchLM leaderboard snapshots.

This is a normalized contract, not an assumed upstream JSON schema.
Published ranks are never calculated from list positions or derived scores.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from math import isfinite
from pathlib import Path
from urllib.parse import quote, urlparse

LEADERBOARD_URL = "https://benchlm.ai/data/leaderboard.json"
LICENSE_URL = "https://benchlm.ai/data"
ATTRIBUTION_TEMPLATE = (
    "Benchmark data and leaderboard rankings from BenchLM.ai, retrieved {retrieved_date}. "
    "BenchLM dataset licensed under MIT. Underlying benchmark results remain "
    "attributed to their original publishers."
)


def attribution(retrieved_date: str) -> str:
    return ATTRIBUTION_TEMPLATE.format(retrieved_date=retrieved_date)


def model_profile_url(model_id: str) -> str:
    return f"https://benchlm.ai/models/{quote(model_id, safe='')}"


def load_leaderboard(path: Path) -> dict:
    if not path.exists():
        return {"source_id": "benchlm", "source_url": LEADERBOARD_URL,
                "status": "unavailable", "records": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1" or payload.get("source_id") != "benchlm":
        raise ValueError("leaderboard must use the normalized BenchLM schema v1")
    if payload.get("source_url") != LEADERBOARD_URL:
        raise ValueError("leaderboard must identify the published BenchLM export")
    date.fromisoformat(payload["retrieved_date"])
    datetime.fromisoformat(payload["source_generated_at"].replace("Z", "+00:00"))
    if payload.get("source_license_url") != LICENSE_URL:
        raise ValueError("leaderboard must retain its dataset license URL")
    if payload.get("attribution") != attribution(payload["retrieved_date"]):
        raise ValueError("leaderboard must retain the required BenchLM attribution")
    seen = set()
    for record in payload["records"]:
        if "source_rank" not in record or "source_score" not in record:
            raise ValueError("leaderboard requires explicit source_rank and source_score fields")
        for field in ("model_id", "configuration_id", "model_name", "evidence_status"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f"leaderboard requires {field}")
        if record.get("lane") not in {"provisional", "verified"}:
            raise ValueError("leaderboard lane must be provisional or verified")
        rank = record.get("source_rank")
        if rank is not None and (type(rank) is not int or rank < 1):
            raise ValueError("source_rank must be a positive published integer or null")
        score = record.get("source_score")
        if score is not None and (type(score) not in {int, float} or not isfinite(score)):
            raise ValueError("source_score must be a finite published number or null")
        profile = urlparse(record.get("profile_url", ""))
        if profile.scheme != "https" or profile.netloc != "benchlm.ai" or not profile.path.startswith("/models/"):
            raise ValueError("leaderboard requires a BenchLM model profile URL")
        key = (record["configuration_id"], record["lane"])
        if key in seen:
            raise ValueError("duplicate configuration in a BenchLM ranking lane")
        seen.add(key)
    return {**payload, "status": "available" if payload["records"] else "unavailable"}


def source_context(results: list, leaderboard: dict) -> dict:
    dates = sorted({row.retrieved_date for row in results if row.source_id == "benchlm"})
    if leaderboard.get("retrieved_date"):
        dates.append(leaderboard["retrieved_date"])
    dates = sorted(set(dates))
    retrieved = " / ".join(dates) if dates else "unavailable"
    return {
        "source_id": "benchlm",
        "source_url": LEADERBOARD_URL,
        "source_license_url": LICENSE_URL,
        "retrieved_date": retrieved,
        "attribution": attribution(retrieved),
        "leaderboard_status": leaderboard["status"],
    }
