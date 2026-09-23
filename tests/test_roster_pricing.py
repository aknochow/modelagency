import json
import tempfile
import unittest
from pathlib import Path

from modelagency.roster_pricing import load_roster_pricing


ROOT = Path(__file__).resolve().parents[1]


class RosterPricingTests(unittest.TestCase):
    def test_checked_in_snapshot_has_public_prices_for_roster_models(self):
        payload = load_roster_pricing(ROOT / "data/normalized/roster_pricing.json")
        self.assertEqual(payload["status"], "available")
        records = {record["model_id"]: record for record in payload["records"]}
        self.assertEqual(records["composer-2-5"]["input_price_per_million_usd"], 0.5)
        self.assertEqual(records["composer-2-5"]["output_price_per_million_usd"], 2.5)
        self.assertEqual(records["gemini-3-1-pro"]["input_price_per_million_usd"], 2)
        self.assertEqual(records["gemini-3-1-pro"]["output_price_per_million_usd"], 12)

    def test_invalid_snapshot_rejects_non_https_pricing_source(self):
        payload = json.loads((ROOT / "data/normalized/roster_pricing.json").read_text())
        payload["records"][0]["pricing_source_url"] = "http://example.com/pricing"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roster-pricing.json"
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                load_roster_pricing(path)


if __name__ == "__main__":
    unittest.main()
