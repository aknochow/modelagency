# modelagency

`modelagency` is a deterministic, provenance-first index of public model and
agent benchmark results, pricing, and task recommendations.

The project deliberately does not call language models. CI fetches permitted
machine-readable source data, validates it, normalizes names, calculates
quality/cost views, renders a static dashboard, and produces a weekly report.

## Source and copyright policy

Every published value must have a source record containing:

- source name and canonical URL;
- retrieval timestamp and source version/build timestamp;
- original benchmark URL when an aggregator is used;
- license/terms URL and redistribution status;
- required attribution text;
- whether the value is copied, derived, or link-only.

The public site will contain facts and derived rankings only where the source
license or written permission allows redistribution. It will not mirror page
HTML, prose, screenshots, logos, benchmark prompts, trajectories, or raw
datasets without permission. Source-specific restrictions are recorded in
`catalog/sources.json` and enforced by the validator.

Artificial Analysis is currently reference-only: its current data terms
restrict raw-data redistribution and prohibit operating a substantially
similar public competitive product without prior written consent. We may link
to it and request permission, but the initial build will not ingest its data.

BenchLM is an initial machine-readable source because its dataset page states
that the dataset is MIT licensed. Underlying benchmark publishers still get
individual attribution; the adapter preserves those evidence URLs.

## Local commands

```bash
python -m modelagency.cli validate
python -m modelagency.cli build
python -m modelagency.cli report
python -m modelagency.cli fetch-benchlm  # explicit network fetch
python -m modelagency.cli slack           # sends only when webhook is configured
python -m unittest discover -s tests -v
```

`build` is offline by default and uses the checked-in normalized fixture. A
future scheduled job will fetch only sources whose catalog entry explicitly
allows it.

## Planned deployment

The generated `site/` directory is suitable for GitHub Pages or GitLab Pages.
The weekly report is Markdown first; a later CI job can post it to Slack via a
webhook without sending any model requests.

See [`docs/SOURCES.md`](docs/SOURCES.md) for the source-by-source rights and
attribution policy.
