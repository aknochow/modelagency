import json
import unittest
from dataclasses import replace
from pathlib import Path

from modelagency.benchlm_metrics import load_metrics
from modelagency.model_policy import is_initial_roster_model, is_model_in_scope
from modelagency.pipeline import (
    DOMAIN_CATEGORIES,
    daily_driver_rows,
    deduplicate_results,
    load_results,
    model_summary_rows,
    portfolio_recommendations,
    recommendations,
)
from modelagency.schema import validate_catalog
from modelagency.sources.benchlm import normalize_payload
from modelagency.sources.terminal_bench import (
    normalize_payload as normalize_terminal_bench_payload,
)
from modelagency.view import dump_view, load_view

ROOT = Path(__file__).resolve().parents[1]


def load_view_from_text(value: str):
    """Use the same parser contract without adding a temporary fixture file."""
    import tempfile

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        return load_view(Path(handle.name))


class ModelAgencyTests(unittest.TestCase):
    def test_catalog_has_no_invalid_entries(self):
        catalog = json.loads((ROOT / "catalog/sources.json").read_text())
        self.assertEqual(validate_catalog(catalog), [])
        self.assertEqual(len(catalog["sources"]), 6)
        terminal = next(source for source in catalog["sources"] if source["id"] == "terminal_bench")
        self.assertEqual(terminal["license"], "Apache-2.0")
        self.assertEqual(terminal["source_status"], "approved")
        self.assertEqual(terminal["data_scope"], "aggregate_leaderboard_results_only")

    def test_checked_in_fixture_is_valid_and_deterministic(self):
        results = load_results(ROOT / "data/normalized/results.json")
        self.assertGreaterEqual(len(results), 0)
        self.assertEqual(
            [(result.category, result.model_name, result.benchmark_id) for result in results],
            sorted((result.category, result.model_name, result.benchmark_id) for result in results),
        )
        self.assertIsInstance(recommendations(results), dict)
        daily_rows = daily_driver_rows(results)
        self.assertTrue(daily_rows)
        self.assertTrue(all(row["category"] == "daily_driver" for row in daily_rows))
        self.assertEqual(
            recommendations(results)["daily_driver"]["best_quality"]["model_name"],
            "Claude Opus 5",
        )
        self.assertEqual(
            recommendations(results)["daily_driver"]["best_value"]["model_name"],
            "GPT-5.6 Luna",
        )
        summaries = model_summary_rows(results)
        self.assertEqual(len(summaries), len({result.model_id for result in results}))
        self.assertTrue(any(summary["category_scores"].get("coding") is not None for summary in summaries))
        self.assertEqual(DOMAIN_CATEGORIES["engineering"], ("coding", "terminal", "cicd"))
        self.assertTrue(all("domain_scores" in summary for summary in summaries))
        self.assertTrue(all(
            summary["cost_tier"] in {1, 2, 3, 4, 5}
            for summary in summaries
            if summary["cost_tier"] is not None
        ))
        self.assertTrue(all(summary["evidence"] for summary in summaries))
        opus_summary = next(summary for summary in summaries if summary["model_name"] == "Claude Opus 5")
        opus_daily = next(row for row in daily_rows if row["model_name"] == "Claude Opus 5")
        self.assertEqual(opus_summary["category_scores"]["coding"], 79.2)
        self.assertEqual(opus_summary["domain_coverage_total"]["engineering"], 3)
        self.assertIn("engineering", recommendations(results))
        luna_summary = next(summary for summary in summaries if summary["model_name"] == "GPT-5.6 Luna")
        self.assertEqual(luna_summary["category_scores"]["administrative"], 83.3)
        self.assertEqual(opus_summary["daily_driver_score"], opus_daily["score"])

    def test_reference_only_sources_are_not_approved(self):
        catalog = json.loads((ROOT / "catalog/sources.json").read_text())
        entries = {source["id"]: source for source in catalog["sources"]}
        self.assertEqual(entries["artificialanalysis_models"]["source_status"], "reference_only")
        self.assertEqual(entries["artificialanalysis_coding_agents"]["source_status"], "reference_only")
        self.assertEqual(entries["deepswe"]["source_status"], "permission_required")

    def test_terminal_bench_normalizer_keeps_effort_and_cost_provenance(self):
        payload = json.loads((ROOT / "tests/fixtures/terminal_bench_leaderboard.json").read_text())
        results = normalize_terminal_bench_payload(payload, retrieved_date="2026-09-09")
        self.assertEqual(len(results), 2)
        luna = next(result for result in results if result.model_id == "gpt-5-6-luna")
        self.assertEqual(luna.model_name, "GPT-5.6 Luna")
        self.assertEqual(luna.configuration_id, "gpt-5-6-luna@max")
        self.assertEqual(luna.effort_level, "max")
        self.assertEqual(luna.agent_id, "codex")
        self.assertEqual(luna.source_total_tokens, 11_600_000_000)
        self.assertEqual(luna.source_trial_count, 330)
        self.assertEqual(luna.source_task_count, 66)
        self.assertAlmostEqual(luna.cost_per_task_usd, 300 / 66)
        self.assertIn("Aggregate leaderboard result only", luna.attribution)
        self.assertEqual(luna.original_source_url, "https://github.com/harbor-framework/terminal-bench")

        opus = next(result for result in results if result.model_id == "claude-opus-5")
        self.assertEqual(opus.model_name, "Claude Opus 5")
        self.assertEqual(opus.configuration_id, "claude-opus-5@max")

    def test_canonical_benchlm_rows_win_over_publisher_duplicates(self):
        results = load_results(ROOT / "data/normalized/results.json")
        benchlm_row = next(result for result in results if result.benchmark_id == "terminalBench4")
        direct_row = replace(benchlm_row, source_id="terminal_bench", score=99.0)
        selected = deduplicate_results([benchlm_row, direct_row])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0], benchlm_row)
        self.assertEqual(selected, deduplicate_results([direct_row, benchlm_row, benchlm_row]))

    def test_effort_configurations_are_separate_modelagency_rows(self):
        results = load_results(ROOT / "data/normalized/results.json")
        luna = next(result for result in results if result.model_id == "gpt-5-6-luna")
        high_effort = replace(
            luna,
            configuration_id="gpt-5-6-luna@high",
            effort_level="high",
        )
        summaries = model_summary_rows(results + [high_effort])
        configuration_ids = {summary["configuration_id"] for summary in summaries}
        self.assertIn("gpt-5-6-luna", configuration_ids)
        self.assertIn("gpt-5-6-luna@high", configuration_ids)
        high_summary = next(summary for summary in summaries if summary["configuration_id"] == "gpt-5-6-luna@high")
        self.assertEqual(high_summary["configuration_label"], "GPT-5.6 Luna (high)")

    def test_portfolio_uses_source_overall_scores_and_fixed_workload_shares(self):
        results = load_results(ROOT / "data/normalized/results.json")
        metrics = load_metrics(ROOT / "data/normalized/benchlm_metrics.json")
        portfolio = portfolio_recommendations(
            model_summary_rows(results),
            monthly_budget_usd=300,
            monthly_input_tokens=20_000_000,
            monthly_output_tokens=5_000_000,
            benchlm_metrics=metrics,
        )
        self.assertEqual([item["share_percent"] for item in portfolio["allocations"]], [10, 30, 60])
        self.assertTrue(all(len(item["options"]) >= 2 for item in portfolio["allocations"]))
        self.assertTrue(all(item["options"][0]["selected"] for item in portfolio["allocations"]))
        self.assertEqual(portfolio["allocations"][0]["model_id"], "claude-mythos-5")
        self.assertEqual(portfolio["allocations"][0]["quality_source"], "BenchLM agentic score")
        luna = next(item for item in portfolio["allocations"] if item["model_id"] == "gpt-5-6-luna")
        self.assertEqual(luna["quality_source"], "BenchLM overall score")
        self.assertAlmostEqual(portfolio["estimated_monthly_cost"], 112.5)

    def test_source_metrics_drive_daily_and_domain_scores(self):
        results = load_results(ROOT / "data/normalized/results.json")
        metrics = load_metrics(ROOT / "data/normalized/benchlm_metrics.json")
        summaries = model_summary_rows(results, benchlm_metrics=metrics)
        luna = next(summary for summary in summaries if summary["model_id"] == "gpt-5-6-luna")
        self.assertEqual(luna["daily_driver_score"], 84.1)
        self.assertEqual(luna["daily_driver_score_basis"], "BenchLM agentic score")
        self.assertEqual(luna["domain_scores"]["engineering"], 84.7)
        self.assertEqual(luna["domain_score_bases"]["engineering"], "BenchLM Terminal-Bench 2.0")
        self.assertEqual(luna["domain_scores"]["management"], 83.3)
        daily = next(row for row in daily_driver_rows(results, benchlm_metrics=metrics) if row["base_model_id"] == "gpt-5-6-luna")
        self.assertEqual(daily["score"], 84.1)
        grok = next(summary for summary in summaries if summary["model_id"] == "grok-4-6")
        self.assertEqual(grok["daily_driver_score"], 70.1)
        self.assertEqual(grok["daily_driver_score_basis"], "BenchLM overall score (agentic unavailable)")
        grok_metric = next(record for record in metrics["records"] if record["model_id"] == "grok-4-6")
        self.assertEqual(grok_metric["overall_score"], 70.08)
        self.assertIsNone(grok_metric["benchmarks"]["terminal_bench_2"]["score"])
        source_recommendations = recommendations(results, benchlm_metrics=metrics)
        self.assertEqual(source_recommendations["daily_driver"]["best_quality"]["model_name"], "GPT-5.6 Sol")
        self.assertEqual(source_recommendations["daily_driver"]["best_value"]["model_name"], "GPT-5.6 Luna")

    def test_portfolio_reuses_a_selected_model_when_distinct_mix_exceeds_budget(self):
        results = load_results(ROOT / "data/normalized/results.json")
        metrics = load_metrics(ROOT / "data/normalized/benchlm_metrics.json")
        summaries = model_summary_rows(results, benchlm_metrics=metrics)
        selected = [
            summary for summary in summaries
            if summary["model_id"] in {
                "claude-fable-5", "claude-opus-4-8", "claude-opus-5",
                "gpt-5-6-luna", "gpt-5-6-sol", "gpt-6-astra",
            }
        ]
        portfolio = portfolio_recommendations(
            selected,
            monthly_budget_usd=300,
            monthly_input_tokens=40_000_000,
            monthly_output_tokens=20_000_000,
            benchlm_metrics=metrics,
        )
        self.assertTrue(portfolio["reused_model"])
        self.assertAlmostEqual(portfolio["estimated_monthly_cost"], 284.0)
        self.assertEqual(portfolio["allocations"][0]["model_id"], "gpt-6-astra")
        self.assertEqual(portfolio["allocations"][1]["model_id"], "gpt-5-6-luna")
        self.assertEqual(portfolio["allocations"][2]["model_id"], "gpt-5-6-luna")

    def test_default_view_is_pasteable_yaml(self):
        view = load_view(ROOT / "catalog/default_view.yaml")
        self.assertEqual(view["models"], [
            "claude-opus-4-8",
            "claude-opus-5",
            "claude-sonnet-5",
            "gpt-5-6-luna",
            "gpt-5-6-sol",
            "gpt-5-6-terra",
            "gpt-6-astra",
            "gemini-3-6-flash",
            "grok-4-6",
            "composer-2-5",
            "gemini-3-1-pro",
        ])
        self.assertEqual(load_view(ROOT / "catalog/default_view.yaml"), load_view_from_text(dump_view(view)))

    def test_gpt6_astra_is_in_the_initial_roster(self):
        self.assertTrue(is_initial_roster_model("GPT-6 Astra", "OpenAI"))

    def test_gemini_31_pro_is_in_the_initial_roster(self):
        self.assertTrue(is_initial_roster_model("Gemini 3.1 Pro", "Google"))

    def test_legacy_claude_opus_and_sonnet_models_are_out_of_scope(self):
        for model_name in (
            "Claude 4 Sonnet",
            "Claude 4.1 Opus",
            "Claude Opus 4.5",
            "Claude Sonnet 4.5 Thinking",
            "Claude Haiku 4.5 Thinking",
            "Claude Opus 4.6 (Adaptive)",
            "Claude Opus 4.7 (Adaptive)",
        ):
            self.assertFalse(is_model_in_scope(model_name))
        for model_name in ("Claude Opus 4.6", "Claude Opus 4.7", "Claude Sonnet 4.6", "Claude Haiku 4.5"):
            self.assertTrue(is_model_in_scope(model_name))

    def test_benchlm_normalizer_preserves_original_credit_and_filters_aa(self):
        models = {
            "generatedAt": "2026-09-08T21:26:54Z",
            "items": [{
                "slug": "gpt-5-6-sol",
                "canonicalModelKey": "gpt-5-6-sol",
                "model": "GPT-5.6 Sol",
                "creator": "OpenAI",
                "url": "https://benchlm.ai/models/gpt-5-6-sol",
                "benchmarks": {"coding": {"swePro": 71.2, "aaCodingIndex": 88.0}},
            }],
        }
        benchmarks = {"items": [
            {
                "benchmarkKey": "swePro",
                "url": "https://benchlm.ai/benchmarks/swe-bench-pro",
                "paperUrl": "https://arxiv.org/abs/2509.16941",
                "authors": "SWE-bench Pro authors",
                "year": 2025,
                "format": "Pass@1",
            },
            {
                "benchmarkKey": "aaCodingIndex",
                "url": "https://benchlm.ai/benchmarks/aacodingindex",
                "paperUrl": "https://artificialanalysis.ai/evaluations/coding",
                "authors": "Artificial Analysis",
                "year": 2026,
                "format": "Index",
            },
        ]}
        pricing = {"items": [{"canonicalModelKey": "gpt-5-6-sol", "inputPrice": 1.2, "outputPrice": 8.4}]}
        results = normalize_payload(models, benchmarks, {"swePro": {"category": "coding", "publish": True}, "aaCodingIndex": {"category": "coding", "publish": True}}, pricing)
        self.assertEqual(len(results), 1)
        self.assertIn("arxiv.org/abs/2509.16941", results[0].attribution)
        self.assertEqual(results[0].original_source_url, "https://arxiv.org/abs/2509.16941")
        self.assertEqual(results[0].input_price_per_million_usd, 1.2)
        self.assertEqual(results[0].output_price_per_million_usd, 8.4)
        self.assertEqual(results[0].source_generated_at, "2026-09-08T21:26:54Z")
        self.assertEqual(results[0].source_model_url, "https://benchlm.ai/models/gpt-5-6-sol")
        refreshed = normalize_payload(models, benchmarks, {"swePro": {"category": "coding", "publish": True}}, pricing, retrieved_date="2026-09-10")
        self.assertEqual(refreshed[0].retrieved_date, "2026-09-10")
        self.assertEqual(refreshed[0].source_generated_at, "2026-09-08T21:26:54Z")


if __name__ == "__main__":
    unittest.main()
