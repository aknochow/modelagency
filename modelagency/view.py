"""Deterministic view configuration helpers.

The project intentionally supports only the small YAML subset used by the
checked-in view file. This keeps the build stdlib-only while making the same
format easy to paste into the dashboard.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

DEFAULT_VIEW_PATH = Path("catalog/default_view.yaml")
BUDGET_DEFAULTS = {
    "monthly_budget_usd": 300,
    "monthly_input_tokens": 20_000_000,
    "monthly_output_tokens": 5_000_000,
}


def _budget_settings(view: dict[str, Any]) -> dict[str, int]:
    settings = {}
    for field, default in BUDGET_DEFAULTS.items():
        value = view.get(field, default)
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            value = int(value)
        maximum = 5000 if field == "monthly_budget_usd" else 1_000_000_000
        if type(value) not in {int, float} or not math.isfinite(value) or value != int(value) or not 0 <= value <= maximum:
            raise ValueError(f"{field} must be a whole number from 0 to {maximum}")
        settings[field] = int(value)
    return settings


def load_view(path: Path) -> dict[str, Any]:
    """Load a simple modelagency view YAML file without third-party packages."""

    lines = path.read_text(encoding="utf-8").splitlines()
    view: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current_list is None:
                raise ValueError(f"list item has no key: {raw_line}")
            view.setdefault(current_list, []).append(_scalar(line[2:].strip()))
            continue
        if ":" not in line:
            raise ValueError(f"unsupported YAML line: {raw_line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            view[key] = _scalar(raw_value)
            current_list = None
        else:
            view[key] = []
            current_list = key
    return normalize_view(view)


def normalize_view(view: dict[str, Any]) -> dict[str, Any]:
    """Return a complete, stable view shape suitable for JSON and the UI."""

    models = [str(value) for value in view.get("models", []) if str(value).strip()]
    agents = [str(value) for value in view.get("agents", []) if str(value).strip()]
    return {
        "version": int(view.get("version", 1)),
        "models": list(dict.fromkeys(models)),
        "agents": list(dict.fromkeys(agents)),
        "search": str(view.get("search", "")),
        "category": str(view.get("category", "")),
        "priced_only": bool(view.get("priced_only", False)),
        "sort": str(view.get("sort", "score")),
        "direction": str(view.get("direction", "desc")),
        **_budget_settings(view),
    }


def dump_view(view: dict[str, Any], *, source_attribution: str | None = None) -> str:
    """Serialize a view using the paste-friendly YAML subset."""

    normalized = normalize_view(view)
    lines = [f"# {source_attribution}"] if source_attribution else []
    if source_attribution:
        lines.append("# Canonical leaderboard and evidence: https://benchlm.ai/llm-agent-benchmarks")
        lines.append("# Work scores and value recommendations are derived by modelagency.")
    lines.append(f"version: {normalized['version']}")
    for key in ("models", "agents"):
        lines.append(f"{key}:")
        lines.extend(f"  - {_quote_yaml(value)}" for value in normalized[key])
    lines.append(f"search: {_quote_yaml(normalized['search'])}")
    lines.append(f"category: {_quote_yaml(normalized['category'])}")
    lines.append(f"priced_only: {'true' if normalized['priced_only'] else 'false'}")
    lines.append(f"sort: {_quote_yaml(normalized['sort'])}")
    lines.append(f"direction: {_quote_yaml(normalized['direction'])}")
    lines.extend(f"{field}: {normalized[field]}" for field in BUDGET_DEFAULTS)
    return "\n".join(lines) + "\n"


def _scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    return value


def _quote_yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
