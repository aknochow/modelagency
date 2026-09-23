# Contributing

Install no runtime dependencies for the initial prototype. Run:

```bash
python -m unittest discover -s tests -v
python -m modelagency.cli validate
python -m modelagency.cli build
```

Before opening a pull request, run a local secret scan when Gitleaks is
available:

```bash
gitleaks dir . --no-banner --redact
```

Do not commit `.env` files, webhook URLs, credentials, internal hostnames, or
private benchmark artifacts. The repository is intended to be safe to publish
without a private configuration file.

To explicitly refresh the permitted BenchLM adapter, run
`python -m modelagency.cli fetch-benchlm`. This performs network access and
must not be used in tests or unattended local builds.

To explicitly refresh the permitted Terminal-Bench adapter, install the
version pinned by CI and run `python -m modelagency.cli fetch-terminal-bench`.
This reads Harbor's aggregate leaderboard JSON only; it must not be used to
download task content, solutions, trajectories, or benchmark artifacts.

`python -m modelagency.cli slack` is a no-op unless
`MODELAGENCY_SLACK_WEBHOOK_URL` is set. Never put that webhook in the
repository or print it in logs.

Network fetchers must be opt-in and must never run during tests or ordinary
builds. New data sources require a provenance and license entry before an
adapter is merged.
