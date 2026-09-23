import json
import tempfile
import unittest
from pathlib import Path

from modelagency.benchlm_metrics import load_metrics

ROOT = Path(__file__).resolve().parents[1]


class BenchLMMetricsTests(unittest.TestCase):
    def test_checked_in_snapshot_preserves_published_values(self):
        payload = load_metrics(ROOT / "data/normalized/benchlm_metrics.json")
        self.assertEqual(payload["status"], "available")
        luna = next(record for record in payload["records"] if record["model_id"] == "gpt-5-6-luna")
        self.assertEqual(luna["agentic_score"], 84.1)
        self.assertEqual(luna["overall_score"], 64.65)
        self.assertEqual(luna["benchmarks"]["terminal_bench_2"]["score"], 84.7)
        self.assertEqual(luna["benchmarks"]["browsecomp"]["score"], 83.3)
        self.assertIsNone(luna["benchmarks"]["osworld_verified"]["score"])
        opus = next(record for record in payload["records"] if record["model_id"] == "claude-opus-4-6")
        self.assertIsNone(opus["agentic_score"])
        self.assertEqual(opus["benchmarks"]["browsecomp"]["score"], 83.7)
        self.assertEqual(opus["benchmarks"]["osworld_verified"]["score"], 72.7)

    def test_invalid_snapshot_rejects_unattributed_benchmark_url(self):
        payload = json.loads((ROOT / "data/normalized/benchlm_metrics.json").read_text())
        payload["records"][0]["benchmarks"]["browsecomp"]["evidence_url"] = "https://example.com"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.json"
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                load_metrics(path)


if __name__ == "__main__":
    unittest.main()
