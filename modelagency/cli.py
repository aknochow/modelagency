"""Command-line entry point for the offline prototype."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
from datetime import UTC, datetime
from http.client import HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

from .benchlm_metrics import load_metrics
from .canonical import load_leaderboard, source_context
from .pipeline import (
    daily_driver_rows,
    load_results,
    model_summary_rows,
    portfolio_recommendations,
    recommendations,
)
from .roster_pricing import load_roster_pricing
from .schema import Result, validate_catalog
from .sources.benchlm import fetch_results
from .sources.terminal_bench import fetch_results as fetch_terminal_bench_results
from .view import load_view

ROOT = Path(__file__).resolve().parents[1]
SITE_VERSION = "v.alpha"
SLACK_WEBHOOK_HOSTS = {"hooks.slack.com", "hooks.slack-gov.com"}
SLACK_WEBHOOK_PATH = re.compile(r"/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+")


def validate() -> int:
    catalog = json.loads((ROOT / "catalog/sources.json").read_text(encoding="utf-8"))
    errors = validate_catalog(catalog)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    load_view(ROOT / "catalog/default_view.yaml")
    results = load_results(ROOT / "data/normalized/results.json")
    load_leaderboard(ROOT / "data/normalized/benchlm_leaderboard.json")
    load_metrics(ROOT / "data/normalized/benchlm_metrics.json")
    load_roster_pricing(ROOT / "data/normalized/roster_pricing.json")
    print(f"validated {len(catalog['sources'])} sources and {len(results)} results")
    return 0


def build() -> int:
    source_payload = json.loads((ROOT / "data/normalized/results.json").read_text(encoding="utf-8"))
    catalog_payload = json.loads((ROOT / "catalog/sources.json").read_text(encoding="utf-8"))
    results = [result for result in load_results(ROOT / "data/normalized/results.json")]
    default_view = load_view(ROOT / "catalog/default_view.yaml")
    leaderboard = load_leaderboard(ROOT / "data/normalized/benchlm_leaderboard.json")
    metrics = load_metrics(ROOT / "data/normalized/benchlm_metrics.json")
    roster_pricing = load_roster_pricing(ROOT / "data/normalized/roster_pricing.json")
    context = source_context(results, leaderboard)
    summaries = model_summary_rows(results, benchlm_metrics=metrics)
    profiles = {row["configuration_id"]: row["profile_url"] for row in leaderboard["records"]}
    sources = {source["id"]: source for source in catalog_payload["sources"]}
    for summary in summaries:
        if summary["configuration_id"] in profiles:
            summary["profile_url"] = profiles[summary["configuration_id"]]
        for evidence in summary["evidence"]:
            evidence["source_status"] = sources[evidence["source_id"]]["source_status"]
    payload = {
        "schema_version": "1",
        "generated_at": source_payload.get("generated_at"),
        "records": [result.to_dict() for result in results] + daily_driver_rows(results, benchlm_metrics=metrics),
        "model_summaries": summaries,
        "recommendations": recommendations(results, benchlm_metrics=metrics),
        "portfolio_recommendations": portfolio_recommendations(
            summaries,
            monthly_budget_usd=default_view["monthly_budget_usd"],
            monthly_input_tokens=default_view["monthly_input_tokens"],
            monthly_output_tokens=default_view["monthly_output_tokens"],
            benchlm_metrics=metrics,
        ),
        "default_view": default_view,
        "benchlm_leaderboard": leaderboard,
        "benchlm_metrics": metrics,
        "roster_pricing": roster_pricing,
        "source_context": context,
    }
    site_data = ROOT / "site/data/results.json"
    site_data.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "site/data/sources.json").write_text(json.dumps(catalog_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "site/data/view.json").write_text(json.dumps(default_view, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "site/data/build.json").write_text(
        json.dumps(
            {"build_date": datetime.now(UTC).date().isoformat(), "version": SITE_VERSION},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"built {len(results)} results")
    return 0


def _load_normalized_payload() -> tuple[dict, list[Result]]:
    payload = json.loads((ROOT / "data/normalized/results.json").read_text(encoding="utf-8"))
    return payload, [Result.from_dict(record) for record in payload.get("records", [])]


def _write_normalized_results(results: list[Result], generated_at: str | None) -> None:
    output = ROOT / "data/normalized/results.json"
    payload = {
        "schema_version": "1",
        "generated_at": generated_at,
        "records": [
            result.to_dict()
            for result in sorted(
                results,
                key=lambda result: (
                    result.category,
                    result.model_name,
                    result.benchmark_id,
                    result.effort_level or "",
                    result.source_id,
                ),
            )
        ],
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _merge_fetched_results(
    existing: list[Result],
    incoming: list[Result],
    *,
    source_id: str,
) -> list[Result]:
    if not incoming:
        return existing
    merged = []
    for result in existing:
        if result.source_id == source_id:
            continue
        merged.append(result)
    return merged + incoming


def report() -> int:
    results = load_results(ROOT / "data/normalized/results.json")
    default_view = load_view(ROOT / "catalog/default_view.yaml")
    leaderboard = load_leaderboard(ROOT / "data/normalized/benchlm_leaderboard.json")
    metrics = load_metrics(ROOT / "data/normalized/benchlm_metrics.json")
    recs = recommendations(results, benchlm_metrics=metrics)
    summaries = model_summary_rows(results, benchlm_metrics=metrics)
    context = source_context(results, leaderboard)
    attribution_text = metrics.get("attribution") if metrics["status"] == "available" else context["attribution"]
    lines = ["# modelagency weekly update", "", attribution_text, "",
             "[BenchLM dataset and license](https://benchlm.ai/data). "
             "BenchLM-backed quality signals are used when published; modelagency derives the documented fallbacks and value views.", ""]
    if metrics["status"] == "available":
        lines.extend(["## BenchLM source metrics", "",
                      "| Model | Agentic | Terminal-Bench 2.0 | BrowseComp | OSWorld-Verified | Overall |",
                      "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for row in metrics["records"]:
            benchmarks = row["benchmarks"]
            values = [
                row.get("agentic_score"),
                benchmarks["terminal_bench_2"].get("score"),
                benchmarks["browsecomp"].get("score"),
                benchmarks["osworld_verified"].get("score"),
                row.get("overall_score"),
            ]
            formatted = ["—" if value is None else f"{value:g}" for value in values]
            lines.append(
                f"| [{row['model_name']}]({row['profile_url']}) | "
                f"{formatted[0]} (#{row.get('agentic_rank') or '—'}) | {formatted[1]} | "
                f"{formatted[2]} | {formatted[3]} | {formatted[4]} (#{row.get('overall_rank') or '—'}) |"
            )
        lines.extend(["", f"Retrieved {metrics['retrieved_date']}; source verified {metrics['source_verified_date']}.", ""])
    if leaderboard["status"] == "available":
        lines.extend(["## BenchLM published leaderboard", "",
                      "| Model | Lane | Published rank | Published score | Evidence status |",
                      "| --- | --- | ---: | ---: | --- |"])
        for row in leaderboard["records"]:
            rank = row["source_rank"] if row["source_rank"] is not None else "—"
            score = row["source_score"] if row["source_score"] is not None else "—"
            lines.append(f"| [{row['model_name']}]({row['profile_url']}) | {row['lane']} | {rank} | {score} | {row['evidence_status']} |")
        lines.append("")
    else:
        lines.extend(["BenchLM published ranks, overall scores, and verification lanes are unavailable in this snapshot. "
                      "[View the canonical leaderboard](https://benchlm.ai/llm-agent-benchmarks).", ""])
    portfolio = portfolio_recommendations(
        summaries,
        monthly_budget_usd=default_view["monthly_budget_usd"],
        monthly_input_tokens=default_view["monthly_input_tokens"],
        monthly_output_tokens=default_view["monthly_output_tokens"],
        benchlm_metrics=metrics,
    )
    if portfolio:
        lines.extend(["## Default workload mix", "",
                      "| Share | Tier | Model | Quality signal | Allocated estimate |",
                      "| ---: | --- | --- | ---: | ---: |"])
        for allocation in portfolio["allocations"]:
            lines.append(
                f"| {allocation['share_percent']}% | {allocation['label']} | {allocation['model_name']} | "
                f"{allocation['quality_score']:.1f} ({allocation['quality_source']}) | "
                f"${allocation['allocated_monthly_cost']:.2f} |"
            )
        lines.extend(["", f"Estimated allocation: ${portfolio['estimated_monthly_cost']:.2f}/month; "
                      f"remaining budget: ${portfolio['remaining_budget']:.2f}.", ""])
    if not recs:
        lines.append("No publishable benchmark records are available yet.")
    for category, category_recs in sorted(recs.items()):
        lines.extend([f"## {category.replace('_', ' ').title()} · source-backed / derived fallback", ""])
        for label, record in category_recs.items():
            if record is None:
                continue
            cost = record["cost_per_task_usd"]
            if cost is None:
                input_price = record["input_price_per_million_usd"]
                output_price = record["output_price_per_million_usd"]
                cost_text = ""
                if input_price is not None and output_price is not None:
                    cost_text = f"token-price proxy ${input_price:g}/${output_price:g} per 1M in/out"
            else:
                cost_text = f"${cost:.4f}/task"
            source_urls = record.get("score_source_urls", [])
            if record.get("score_source_url"):
                source_urls = [record["score_source_url"]]
            if source_urls:
                basis = record.get("score_basis") or record.get("daily_driver_score_basis") or "BenchLM source score"
                evidence = " · ".join(f"[{basis}]({url})" for url in source_urls)
            else:
                evidence = f"[{record['source_id']}]({record['evidence_url']})"
            original = f"; [original benchmark]({record['original_source_url']})" if record["original_source_url"] else ""
            model_label = record.get("configuration_label", record["model_name"])
            if record.get("profile_url"):
                model_label = f"[{model_label}]({record['profile_url']})"
            cost_suffix = f"; {cost_text}" if cost_text else ""
            lines.append(f"- **{label.replace('_', ' ').title()}**: {model_label} — {record['score']} {record['score_unit']}{cost_suffix}; {evidence}{original}")
        lines.append("")
    report_path = ROOT / "reports/weekly.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(report_path)
    return 0


def fetch_benchlm() -> int:
    results = fetch_results(ROOT)
    existing_payload, existing = _load_normalized_payload()
    merged = _merge_fetched_results(existing, results, source_id="benchlm")
    generated_at = f"{results[0].retrieved_date}T00:00:00Z" if results else existing_payload.get("generated_at")
    _write_normalized_results(merged, generated_at)
    print(f"fetched {len(results)} publishable BenchLM records")
    return 0


def fetch_terminal_bench() -> int:
    results = fetch_terminal_bench_results()
    existing_payload, existing = _load_normalized_payload()
    merged = _merge_fetched_results(
        existing,
        results,
        source_id="terminal_bench",
    )
    generated_at = f"{results[0].retrieved_date}T00:00:00Z" if results else existing_payload.get("generated_at")
    _write_normalized_results(merged, generated_at)
    print(f"fetched {len(results)} publishable Terminal-Bench records")
    return 0


def _slack_webhook_target(value: str) -> tuple[str, str]:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in SLACK_WEBHOOK_HOSTS
        or parsed.port is not None
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not SLACK_WEBHOOK_PATH.fullmatch(parsed.path)
    ):
        raise ValueError("MODELAGENCY_SLACK_WEBHOOK_URL must be a supported HTTPS Slack webhook")
    return parsed.hostname, parsed.path


def slack() -> int:
    webhook = os.environ.get("MODELAGENCY_SLACK_WEBHOOK_URL")
    if not webhook:
        print("Slack not configured; report generated locally only")
        return 0
    host, path = _slack_webhook_target(webhook)
    report()
    report_text = (ROOT / "reports/weekly.md").read_text(encoding="utf-8")
    connection = HTTPSConnection(host, timeout=30, context=ssl.create_default_context())
    try:
        connection.request(
            "POST",
            path,
            body=json.dumps({"text": report_text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"Slack webhook returned HTTP {response.status}")
    finally:
        connection.close()
    print("Slack report sent")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="modelagency")
    parser.add_argument("command", choices=("validate", "build", "report", "fetch-benchlm", "fetch-terminal-bench", "slack"))
    args = parser.parse_args()
    return {
        "validate": validate,
        "build": build,
        "report": report,
        "fetch-benchlm": fetch_benchlm,
        "fetch-terminal-bench": fetch_terminal_bench,
        "slack": slack,
    }[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
