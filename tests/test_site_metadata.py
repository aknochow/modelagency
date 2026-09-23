import json
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteMetadataTests(unittest.TestCase):
    def test_build_metadata_has_alpha_version_and_iso_date(self):
        metadata = json.loads((ROOT / "site/data/build.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["version"], "v.alpha")
        self.assertEqual(date.fromisoformat(metadata["build_date"]).isoformat(), metadata["build_date"])

    def test_site_pages_include_shared_footer(self):
        for page_name in ("index.html", "pricing.html", "sources.html"):
            page = (ROOT / "site" / page_name).read_text(encoding="utf-8")
            self.assertIn('class="site-footer"', page)
            self.assertIn('data-site-version', page)
            self.assertIn('data-site-build-date', page)
            self.assertIn('src="footer.js?v=20260914-1"', page)

    def test_budget_usage_is_always_expanded(self):
        page = (ROOT / "site/index.html").read_text(encoding="utf-8")
        self.assertIn('<div class="budget-assumptions" id="usage-assumptions">', page)
        self.assertIn("<h3>Expected Usage</h3>", page)
        self.assertNotIn('<details class="budget-assumptions"', page)
        self.assertNotIn("<summary>Expected Usage</summary>", page)
