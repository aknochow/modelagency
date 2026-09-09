# Contributing

Install no runtime dependencies for the initial prototype. Run:

```bash
python -m unittest discover -s tests -v
python -m modelagency.cli validate
python -m modelagency.cli build
```

To explicitly refresh the permitted BenchLM adapter, run
`python -m modelagency.cli fetch-benchlm`. This performs network access and
must not be used in tests or unattended local builds.

`python -m modelagency.cli slack` is a no-op unless
`MODELAGENCY_SLACK_WEBHOOK_URL` is set. Never put that webhook in the
repository or print it in logs.

Network fetchers must be opt-in and must never run during tests or ordinary
builds. New data sources require a provenance and license entry before an
adapter is merged.
