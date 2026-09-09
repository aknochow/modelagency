"""Command-line entry point for the offline prototype."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .pipeline import load_results, recommendations
from .schema import validate_catalog
from .sources.benchlm import fetch_results


ROOT = Path(__file__).resolve().parents[1]


def validate() -> int:
    catalog = json.loads((ROOT / "catalog/sources.json").read_text(encoding="utf-8"))
    errors = validate_catalog(catalog)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    results = load_results(ROOT / "data/normalized/results.json")
    print(f"validated {len(catalog['sources'])} sources and {len(results)} results")
    return 0


def build() -> int:
    source_payload = json.loads((ROOT / "data/normalized/results.json").read_text(encoding="utf-8"))
    catalog_payload = json.loads((ROOT / "catalog/sources.json").read_text(encoding="utf-8"))
    results = [result for result in load_results(ROOT / "data/normalized/results.json")]
    payload = {
        "schema_version": "1",
        "generated_at": source_payload.get("generated_at"),
        "records": [result.__dict__ for result in results],
        "recommendations": recommendations(results),
    }
    site_data = ROOT / "site/data/results.json"
    site_data.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "site/data/sources.json").write_text(json.dumps(catalog_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"built {len(results)} results")
    return 0


def report() -> int:
    results = load_results(ROOT / "data/normalized/results.json")
    recs = recommendations(results)
    lines = ["# modelagency weekly update", "", f"Generated: {date.today().isoformat()}", ""]
    if not recs:
        lines.append("No publishable benchmark records are available yet.")
    for category, category_recs in sorted(recs.items()):
        lines.extend([f"## {category.title()}", ""])
        for label, record in category_recs.items():
            if record is None:
                continue
            cost = record["cost_per_task_usd"]
            if cost is None:
                input_price = record["input_price_per_million_usd"]
                output_price = record["output_price_per_million_usd"]
                cost_text = "task cost unknown"
                if input_price is not None and output_price is not None:
                    cost_text += f"; token price ${input_price:g}/${output_price:g} per 1M in/out"
            else:
                cost_text = f"${cost:.4f}/task"
            evidence = f"[{record['source_id']}]({record['evidence_url']})"
            original = f"; [original benchmark]({record['original_source_url']})" if record["original_source_url"] else ""
            lines.append(f"- **{label.replace('_', ' ').title()}**: {record['model_name']} — {record['score']} {record['score_unit']}; {cost_text}; {evidence}{original}")
        lines.append("")
    report_path = ROOT / "reports/weekly.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(report_path)
    return 0


def fetch_benchlm() -> int:
    results = fetch_results(ROOT)
    payload = {
        "schema_version": "1",
        "generated_at": f"{results[0].retrieved_date}T00:00:00Z" if results else None,
        "records": [result.__dict__ for result in results],
    }
    output = ROOT / "data/normalized/results.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"fetched {len(results)} publishable BenchLM records")
    return 0


def slack() -> int:
    webhook = os.environ.get("MODELAGENCY_SLACK_WEBHOOK_URL")
    if not webhook:
        print("Slack not configured; report generated locally only")
        return 0
    if urlparse(webhook).scheme != "https":
        raise ValueError("MODELAGENCY_SLACK_WEBHOOK_URL must be an HTTPS URL")
    report()
    report_text = (ROOT / "reports/weekly.md").read_text(encoding="utf-8")
    request = Request(
        webhook,
        data=json.dumps({"text": report_text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30):  # noqa: S310 - webhook URL is supplied explicitly by CI.
        pass
    print("Slack report sent")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="modelagency")
    parser.add_argument("command", choices=("validate", "build", "report", "fetch-benchlm", "slack"))
    args = parser.parse_args()
    return {"validate": validate, "build": build, "report": report, "fetch-benchlm": fetch_benchlm, "slack": slack}[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
