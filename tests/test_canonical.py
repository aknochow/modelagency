import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from modelagency.canonical import attribution, load_leaderboard, source_context
from modelagency.cli import _merge_fetched_results, _slack_webhook_target
from modelagency.pipeline import configuration_id, deduplicate_results, load_results, model_summary_rows
from modelagency.sources.benchlm import MODELS_URL, fetch_json, fetch_results
from modelagency.view import dump_view, load_view, normalize_view

ROOT = Path(__file__).resolve().parents[1]


class CanonicalTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "tests/fixtures/benchlm_canonical_contract.json").read_text())

    def load_payload(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leaderboard.json"
            path.write_text(json.dumps(payload))
            return load_leaderboard(path)

    def test_source_ranks_scores_and_lanes_are_preserved_exactly(self):
        result = self.load_payload(self.payload)
        self.assertEqual(result["records"], self.payload["records"])
        self.assertEqual([row["source_rank"] for row in result["records"]], [47, 12])
        self.assertEqual(result["source_generated_at"], "2026-09-09T10:00:00Z")
        self.assertEqual(result["retrieved_date"], "2026-09-10")

    def test_absent_published_values_stay_absent(self):
        self.payload["records"][0]["source_rank"] = None
        self.payload["records"][0]["source_score"] = None
        result = self.load_payload(self.payload)
        self.assertIsNone(result["records"][0]["source_rank"])
        self.assertIsNone(result["records"][0]["source_score"])
        with tempfile.TemporaryDirectory() as directory:
            result = load_leaderboard(Path(directory) / "missing.json")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["records"], [])

    def test_invalid_source_fields_fail_validation(self):
        for field, value in (("source_rank", 0), ("source_rank", True),
                             ("source_score", float("nan")), ("source_score", True),
                             ("lane", "derived"), ("profile_url", "javascript:alert(1)"),
                             ("evidence_status", "")):
            with self.subTest(field=field, value=value):
                payload = copy.deepcopy(self.payload)
                payload["records"][0][field] = value
                with self.assertRaises(ValueError):
                    self.load_payload(payload)
        self.payload["records"].append(self.payload["records"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load_payload(self.payload)

    def test_publisher_refresh_preserves_canonical_evidence(self):
        canonical = load_results(ROOT / "data/normalized/results.json")[0]
        direct = replace(canonical, source_id="terminal_bench", score=99.0)
        for existing, incoming, source_id in (([canonical], [direct], "terminal_bench"),
                                              ([direct], [canonical], "benchlm")):
            merged = _merge_fetched_results(existing, incoming, source_id=source_id)
            self.assertEqual(len(merged), 2)
            self.assertIn(canonical, merged)
            self.assertEqual(deduplicate_results(merged), [canonical])

    def test_duplicate_selection_is_independent_of_input_order(self):
        canonical = load_results(ROOT / "data/normalized/results.json")[0]
        updated = replace(canonical, score=canonical.score + 1, retrieved_date="2026-09-11")
        self.assertEqual(deduplicate_results([updated, canonical, updated]), [updated])
        self.assertEqual(deduplicate_results([canonical, updated]), [updated])
        high = replace(canonical, configuration_id=canonical.model_id + "@high", effort_level="high")
        self.assertEqual(len(deduplicate_results([canonical, high])), 2)

    def test_reference_only_rows_do_not_enter_rankings(self):
        canonical = load_results(ROOT / "data/normalized/results.json")[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            path.write_text(json.dumps({"records": [
                canonical.to_dict(),
                replace(canonical, source_id="artificialanalysis_models", score=100).to_dict(),
                replace(canonical, source_id="unknown", score=100).to_dict(),
            ]}))
            self.assertEqual(load_results(path), [canonical])

    def test_agent_runs_are_distinct_from_model_level_results(self):
        canonical = load_results(ROOT / "data/normalized/results.json")[0]
        agent_run = replace(canonical, source_id="terminal_bench", agent_id="example-agent")
        self.assertNotEqual(configuration_id(canonical), configuration_id(agent_run))
        self.assertEqual(len(deduplicate_results([canonical, agent_run])), 2)
        self.assertEqual(len(model_summary_rows([canonical, agent_run])), 2)

    def test_reference_only_policy_prevents_network_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog").mkdir()
            (root / "catalog/sources.json").write_text(json.dumps({"sources": [
                {"id": "benchlm", "source_status": "reference_only", "redistribution": "prohibited"}
            ]}))
            with patch("modelagency.sources.benchlm.fetch_json") as fetch:
                with self.assertRaisesRegex(ValueError, "does not permit"):
                    fetch_results(root)
                fetch.assert_not_called()

    def test_benchlm_fetch_uses_fixed_https_host_and_path(self):
        response = Mock(status=200)
        response.read.return_value = b'{"items": []}'
        connection = Mock()
        connection.getresponse.return_value = response
        with patch("modelagency.sources.benchlm.HTTPSConnection", return_value=connection) as connection_factory:
            self.assertEqual(fetch_json(MODELS_URL), {"items": []})
        connection_factory.assert_called_once()
        self.assertEqual(connection_factory.call_args.args[0], "benchlm.ai")
        self.assertEqual(connection_factory.call_args.kwargs["timeout"], 30)
        connection.request.assert_called_once_with(
            "GET", "/data/models.json", headers={"User-Agent": "modelagency/0.1"}
        )
        connection.close.assert_called_once_with()

    def test_benchlm_fetch_rejects_urls_outside_the_allowlist(self):
        with self.assertRaisesRegex(ValueError, "allowlist"):
            fetch_json("https://example.invalid/data.json")

    def test_slack_webhook_target_requires_an_allowlisted_host_and_path(self):
        self.assertEqual(
            _slack_webhook_target("https://hooks.slack.com/services/T000/B000/test"),
            ("hooks.slack.com", "/services/T000/B000/test"),
        )
        for value in (
            "http://hooks.slack.com/services/T000/B000/test",
            "https://example.invalid/services/T000/B000/test",
            "https://hooks.slack.com/redirect",
            "https://hooks.slack.com/services/T000/B000/test?next=example.invalid",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "supported HTTPS Slack webhook"):
                _slack_webhook_target(value)

    def test_export_attribution_preserves_view_round_trip(self):
        view = load_view(ROOT / "catalog/default_view.yaml")
        credit = attribution("2026-09-10")
        exported = dump_view(view, source_attribution=credit)
        self.assertIn(credit, exported)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.yaml"
            path.write_text(exported)
            self.assertEqual(load_view(path), view)

    def test_legacy_views_receive_budget_defaults_without_changing_selection(self):
        view = normalize_view({"models": [], "agents": ["model-level"]})
        self.assertEqual(view["models"], [])
        self.assertEqual(view["monthly_budget_usd"], 300)
        self.assertEqual(view["monthly_input_tokens"], 20_000_000)
        self.assertEqual(view["monthly_output_tokens"], 5_000_000)

    def test_budget_yaml_is_plain_and_round_trips(self):
        view = normalize_view({"monthly_budget_usd": 5000, "monthly_input_tokens": 0,
                               "monthly_output_tokens": 700_000})
        serialized = dump_view(view)
        self.assertTrue(serialized.startswith("version: 1\n"))
        self.assertNotIn("#", serialized)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.yaml"
            path.write_text(serialized)
            self.assertEqual(load_view(path), view)

    def test_invalid_budget_settings_are_rejected(self):
        for field, value in (("monthly_budget_usd", -1), ("monthly_budget_usd", 5001),
                             ("monthly_budget_usd", True), ("monthly_budget_usd", None),
                             ("monthly_input_tokens", float("inf")),
                             ("monthly_output_tokens", 1.5), ("monthly_output_tokens", "oops")):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    normalize_view({field: value})

    def test_source_context_keeps_multiple_retrieval_dates(self):
        original = load_results(ROOT / "data/normalized/results.json")[0]
        older = replace(original, retrieved_date="2026-09-09")
        context = source_context([older, original], {"status": "unavailable"})
        self.assertEqual(context["retrieved_date"], "2026-09-09 / 2026-09-10")


if __name__ == "__main__":
    unittest.main()
