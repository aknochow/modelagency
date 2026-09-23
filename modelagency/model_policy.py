"""Deterministic model-roster policy for the initial dashboard."""

from __future__ import annotations

import re

_CLAUDE_FAMILY_VERSION = re.compile(
    r"^Claude\s+(?:(?P<family>Opus|Sonnet)\s+(?P<major>\d+)(?:\.(?P<minor>\d+))?|"
    r"(?P<major_alt>\d+)(?:\.(?P<minor_alt>\d+))?\s+(?P<family_alt>Opus|Sonnet))\b",
    re.IGNORECASE,
)
_MINIMUM_CLAUDE_FAMILY_VERSION = (4, 6)
_REASONING_PROFILE = re.compile(r"\b(?:thinking|adaptive)\b", re.IGNORECASE)
_INITIAL_ROSTER_MODEL = re.compile(
    r"^(?:"
    r"claude\s+"
    r"|gpt[- ]5(?:\.6|[- ]6)\b"
    r"|gpt[- ]6[- ]astra\b"
    r"|grok[- ]4(?:\.6|[- ]6)\b"
    r"|gemini[- ]3(?:\.1|[- ]1)\s+pro\b"
    r"|gemini[- ]3(?:\.6|[- ]6|\.7|[- ]7|\.8|[- ]8)\b"
    r")",
    re.IGNORECASE,
)


def is_model_in_scope(model_name: str) -> bool:
    """Return whether a model belongs in the current tracked roster.

    Claude Opus and Sonnet versions older than 4.6 are intentionally omitted.
    Explicit thinking/adaptive reasoning profiles are also omitted because
    the initial roster tracks the standard models available to the team.
    """

    name = str(model_name).strip()
    if _REASONING_PROFILE.search(name):
        return False
    match = _CLAUDE_FAMILY_VERSION.match(name)
    if not match:
        return True
    major = int(match.group("major") or match.group("major_alt"))
    minor = int(match.group("minor") or match.group("minor_alt") or 0)
    return (major, minor) >= _MINIMUM_CLAUDE_FAMILY_VERSION


def is_initial_roster_model(model_name: str, provider: str | None = None) -> bool:
    """Return whether a source row belongs to the initial tracked roster.

    Some leaderboards abbreviate Anthropic display names to ``Opus 5`` or
    ``Sonnet 5`` and carry the provider separately.  Callers should normalize
    those labels before invoking this helper when possible.
    """

    name = str(model_name).strip()
    provider_name = str(provider or "").strip().lower()
    candidate = name
    if provider_name == "anthropic" and re.match(
        r"^(?:opus|sonnet|fable|mythos|haiku)\b", name, re.IGNORECASE
    ):
        candidate = f"Claude {name}"
    return is_model_in_scope(candidate) and bool(_INITIAL_ROSTER_MODEL.match(candidate))
