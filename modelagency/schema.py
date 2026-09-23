"""Small stdlib-only schema and validation layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

ALLOWED_EVALUATION_TYPES = {"objective", "human_preference", "reported", "estimated", "derived"}
ALLOWED_DERIVATION_TYPES = {"copied_fact", "derived", "link_only"}


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


@dataclass(frozen=True)
class Result:
    model_id: str
    model_name: str
    provider: str
    agent_id: str | None
    category: str
    benchmark_id: str
    benchmark_version: str
    score: float
    score_unit: str
    cost_per_task_usd: float | None
    cost_basis: str | None
    input_price_per_million_usd: float | None
    output_price_per_million_usd: float | None
    pricing_source_url: str | None
    source_id: str
    source_url: str
    evidence_url: str
    original_source_url: str | None
    source_license_url: str
    retrieved_date: str
    evaluation_type: str
    derivation_type: str
    attribution: str
    source_total_cost_usd: float | None = None
    source_total_tokens: int | None = None
    source_trial_count: int | None = None
    source_task_count: int | None = None
    configuration_id: str | None = None
    effort_level: str | None = None
    source_generated_at: str | None = None
    source_model_url: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Result:
        required = (
            "model_id", "model_name", "provider", "category", "benchmark_id",
            "benchmark_version", "score", "score_unit", "source_id", "source_url",
            "evidence_url", "source_license_url", "retrieved_date", "evaluation_type",
            "derivation_type", "attribution",
        )
        missing = [key for key in required if key not in raw]
        if missing:
            raise ValueError(f"result missing required fields: {', '.join(missing)}")
        result = cls(**{field: raw.get(field) for field in cls.__dataclass_fields__})
        result.validate()
        return result

    def validate(self) -> None:
        if not self.model_id or not self.model_name or not self.provider:
            raise ValueError("model identity fields must be non-empty")
        if not self.category or not self.benchmark_id or not self.benchmark_version:
            raise ValueError("benchmark identity fields must be non-empty")
        if not isinstance(self.score, (int, float)) or self.score < 0:
            raise ValueError("score must be a non-negative number")
        if not _is_https_url(self.source_url) or not _is_https_url(self.evidence_url):
            raise ValueError("source_url and evidence_url must be HTTPS URLs")
        if self.original_source_url and not _is_https_url(self.original_source_url):
            raise ValueError("original_source_url must be HTTPS when present")
        if not _is_https_url(self.source_license_url):
            raise ValueError("source_license_url must be HTTPS")
        if self.source_model_url and not _is_https_url(self.source_model_url):
            raise ValueError("source_model_url must be HTTPS when present")
        if self.source_generated_at:
            datetime.fromisoformat(self.source_generated_at.replace("Z", "+00:00"))
        for field in ("configuration_id", "effort_level"):
            value = getattr(self, field)
            if value is not None and not value.strip():
                raise ValueError(f"{field} must be non-empty when present")
        if self.evaluation_type not in ALLOWED_EVALUATION_TYPES:
            raise ValueError(f"unsupported evaluation_type: {self.evaluation_type}")
        if self.derivation_type not in ALLOWED_DERIVATION_TYPES:
            raise ValueError(f"unsupported derivation_type: {self.derivation_type}")
        if self.cost_per_task_usd is not None and self.cost_per_task_usd < 0:
            raise ValueError("cost_per_task_usd must be non-negative")
        for field in ("input_price_per_million_usd", "output_price_per_million_usd"):
            value = getattr(self, field)
            if value is not None and value < 0:
                raise ValueError(f"{field} must be non-negative")
        for field in (
            "source_total_cost_usd",
            "source_total_tokens",
            "source_trial_count",
            "source_task_count",
        ):
            value = getattr(self, field)
            if value is not None and value < 0:
                raise ValueError(f"{field} must be non-negative")
        if self.pricing_source_url and not _is_https_url(self.pricing_source_url):
            raise ValueError("pricing_source_url must be HTTPS when present")
        if not self.attribution.strip():
            raise ValueError("attribution is required")

    def to_dict(self) -> dict[str, Any]:
        """Serialize a result without expanding absent optional metadata."""

        record = dict(self.__dict__)
        for field in (
            "source_generated_at",
            "source_model_url",
            "source_total_cost_usd",
            "source_total_tokens",
            "source_trial_count",
            "source_task_count",
        ):
            if record.get(field) is None:
                record.pop(field, None)
        return record


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, source in enumerate(catalog.get("sources", [])):
        source_id = source.get("id")
        if not source_id:
            errors.append(f"sources[{index}] has no id")
            continue
        if source_id in seen:
            errors.append(f"duplicate source id: {source_id}")
        seen.add(source_id)
        for field in ("canonical_url", "license_url"):
            if source.get(field) and not _is_https_url(source[field]):
                errors.append(f"{source_id}.{field} must be HTTPS")
        if source.get("source_status") not in {"approved", "permission_required", "reference_only"}:
            errors.append(f"{source_id}.source_status is invalid")
        if not source.get("attribution"):
            errors.append(f"{source_id} is missing attribution")
        if source.get("source_status") == "approved":
            if not source.get("license"):
                errors.append(f"{source_id} is approved but has no license")
            if source.get("redistribution") not in {"allowed", "allowed_with_attribution"}:
                errors.append(f"{source_id} approved status has invalid redistribution policy")
    return errors
