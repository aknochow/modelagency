# modelagency contribution notes

This is a standalone Python project. Keep all collection, normalization,
ranking, and report generation deterministic and offline-testable.

Before adding a source:

1. Read its license, terms, attribution, and redistribution conditions.
2. Add a complete entry to `catalog/sources.json`.
3. Prefer an official API, JSON, CSV, or repository export over scraping HTML.
4. Record the original evidence URL for every normalized result.
5. Add a fixture and validation test; never require network access in tests.

Do not add model/API credentials, benchmark prompts, trajectories, logos, or
copied source prose. Use `source_status=permission_required` when the legal
position is unclear. A source marked `reference_only` must not be fetched by
the production pipeline.

Commits should use DCO sign-off (`git commit -s`) and include an
`Assisted-by: Claude (<model-id>)` trailer for AI-assisted commits.
