import json
import unittest
from pathlib import Path

from modelagency.pipeline import load_results, recommendations
from modelagency.schema import validate_catalog
from modelagency.sources.benchlm import normalize_payload


ROOT = Path(__file__).resolve().parents[1]


class ModelAgencyTests(unittest.TestCase):
    def test_catalog_has_no_invalid_entries(self):
        catalog = json.loads((ROOT / "catalog/sources.json").read_text())
        self.assertEqual(validate_catalog(catalog), [])

    def test_checked_in_fixture_is_valid_and_deterministic(self):
        results = load_results(ROOT / "data/normalized/results.json")
        self.assertGreaterEqual(len(results), 0)
        self.assertEqual(
            [(result.category, result.model_name, result.benchmark_id) for result in results],
            sorted((result.category, result.model_name, result.benchmark_id) for result in results),
        )
        self.assertIsInstance(recommendations(results), dict)

    def test_reference_only_sources_are_not_approved(self):
        catalog = json.loads((ROOT / "catalog/sources.json").read_text())
        entries = {source["id"]: source for source in catalog["sources"]}
        self.assertEqual(entries["artificialanalysis_models"]["source_status"], "reference_only")
        self.assertEqual(entries["artificialanalysis_coding_agents"]["source_status"], "reference_only")
        self.assertEqual(entries["deepswe"]["source_status"], "permission_required")

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


if __name__ == "__main__":
    unittest.main()
