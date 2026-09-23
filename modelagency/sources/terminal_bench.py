"""Harbor Terminal-Bench leaderboard adapter.

The adapter consumes only the aggregate JSON returned by Harbor's public
leaderboard read command.  It deliberately does not download task prompts,
solutions, trajectories, or benchmark artifacts.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from ..model_policy import is_initial_roster_model
from ..schema import Result

SOURCE_ID = "terminal_bench"
LEADERBOARD_SLUG = "terminal-bench/terminal-bench/4-0-0"
LEADERBOARD_URL = (
    "https://hub.harborframework.com/datasets/terminal-bench/terminal-bench/latest"
    "?tab=leaderboard&leaderboard=4-0-0"
)
BENCHMARK_URL = "https://github.com/harbor-framework/terminal-bench"
LICENSE_URL = f"{BENCHMARK_URL}/blob/main/LICENSE"
BENCHMARK_ID = "terminalBench4"
BENCHMARK_VERSION = "4.0.0"
TASK_COUNT = 66


def _label(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("label") or value.get("name") or value.get("id") or "").strip()
    return str(value or "").strip()


def _url(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("url")
    value = str(value or "").strip()
    return value if value.startswith("https://") else None


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value


def _canonical_model_name(label: str, provider: str) -> str:
    if provider.lower() == "anthropic" and re.match(
        r"^(?:opus|sonnet|fable|mythos|haiku)\b", label, re.IGNORECASE
    ):
        return f"Claude {label}"
    return label


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return leaderboard rows from the public Harbor JSON response."""

    candidates: Any = payload
    if isinstance(payload.get("rows"), list):
        candidates = payload["rows"]
    elif isinstance(payload.get("results"), list):
        candidates = payload["results"]
    elif isinstance(payload.get("entries"), list):
        candidates = payload["entries"]
    elif isinstance(payload.get("data"), list):
        candidates = payload["data"]
    elif isinstance(payload.get("leaderboard"), dict):
        nested = payload["leaderboard"]
        for key in ("rows", "results", "entries", "data"):
            if isinstance(nested.get(key), list):
                candidates = nested[key]
                break
    return [row for row in candidates if isinstance(row, dict)] if isinstance(candidates, list) else []


def _version(payload: dict[str, Any]) -> str:
    leaderboard = payload.get("leaderboard") if isinstance(payload.get("leaderboard"), dict) else {}
    raw = str(
        payload.get("benchmark_version")
        or payload.get("dataset_version")
        or leaderboard.get("dataset_version")
        or leaderboard.get("name")
        or BENCHMARK_VERSION
    )
    return raw.replace("-", ".") if re.fullmatch(r"\d+(?:-\d+)+", raw) else raw


def normalize_payload(payload: dict[str, Any], *, retrieved_date: str | None = None) -> list[Result]:
    """Normalize Harbor aggregate rows without copying task-level content."""

    retrieved = retrieved_date or datetime.now(UTC).date().isoformat()
    version = _version(payload)
    results: list[Result] = []
    for row in _rows(payload):
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        provider = _label(metadata.get("model_org")) or "Unknown"
        raw_model_name = _label(metadata.get("model_display"))
        model_name = _canonical_model_name(raw_model_name, provider)
        if not model_name or not is_initial_roster_model(model_name, provider):
            continue
        score = metrics.get("accuracy")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        model_id = str(
            row.get("model_id")
            or metadata.get("model_id")
            or _slug(model_name)
        ).strip()
        if not model_id:
            continue
        effort = str(metadata.get("reasoning_effort") or "").strip() or None
        configuration_id = f"{model_id}@{effort}" if effort else model_id
        agent_name = _label(metadata.get("agent_display"))
        agent_id = _slug(agent_name) if agent_name else None
        total_cost = metrics.get("total_cost_usd")
        if not isinstance(total_cost, (int, float)) or isinstance(total_cost, bool):
            total_cost = None
        total_tokens = metrics.get("total_tokens")
        if not isinstance(total_tokens, (int, float)) or isinstance(total_tokens, bool):
            total_tokens = None
        trial_count = metrics.get("n_trials")
        if not isinstance(trial_count, (int, float)) or isinstance(trial_count, bool):
            trial_count = None
        task_count = metrics.get("task_count")
        if not isinstance(task_count, (int, float)) or isinstance(task_count, bool):
            task_count = TASK_COUNT if version.startswith("4.0") else None
        cost_per_task = total_cost / task_count if total_cost is not None and task_count else None
        evidence_url = _url(row.get("evidence_url")) or LEADERBOARD_URL
        source_attribution = (
            f"Source: Harbor Terminal-Bench {version} leaderboard ({LEADERBOARD_URL}), "
            f"retrieved {retrieved}; benchmark: Terminal-Bench contributors "
            f"({BENCHMARK_URL}). Aggregate leaderboard result only; task content "
            "and benchmark artifacts are not redistributed."
        )
        cost_basis = None
        if cost_per_task is not None:
            cost_basis = (
                f"Derived from Harbor's total submission cost divided by {int(task_count)} "
                f"Terminal-Bench {version} tasks; source total includes all reported trials"
            )
        results.append(Result(
            model_id=model_id,
            model_name=model_name,
            provider=provider,
            agent_id=agent_id,
            category="terminal",
            benchmark_id=BENCHMARK_ID,
            benchmark_version=version,
            score=float(score),
            score_unit="accuracy (%)",
            cost_per_task_usd=cost_per_task,
            cost_basis=cost_basis,
            input_price_per_million_usd=None,
            output_price_per_million_usd=None,
            pricing_source_url=None,
            source_id=SOURCE_ID,
            source_url=LEADERBOARD_URL,
            evidence_url=evidence_url,
            original_source_url=BENCHMARK_URL,
            source_license_url=LICENSE_URL,
            retrieved_date=retrieved,
            evaluation_type="reported",
            derivation_type="copied_fact",
            attribution=source_attribution,
            source_total_cost_usd=total_cost,
            source_total_tokens=int(total_tokens) if total_tokens is not None else None,
            source_trial_count=int(trial_count) if trial_count is not None else None,
            source_task_count=int(task_count) if task_count is not None else None,
            configuration_id=configuration_id,
            effort_level=effort,
        ))
    return sorted(results, key=lambda result: (result.category, result.model_name, result.effort_level or ""))


def fetch_payload(harbor_bin: str | None = None) -> dict[str, Any]:
    """Read the public leaderboard through Harbor's documented JSON command."""

    executable = harbor_bin or shutil.which("harbor")
    if not executable:
        raise RuntimeError(
            "Harbor CLI is required for Terminal-Bench fetching; install a pinned "
            "Harbor release before running this network command"
        )
    completed = subprocess.run(
        [executable, "hub", "leaderboard", "show", LEADERBOARD_SLUG, "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise TypeError("Harbor leaderboard response must be a JSON object")
    return payload


def fetch_results() -> list[Result]:
    return normalize_payload(fetch_payload())
