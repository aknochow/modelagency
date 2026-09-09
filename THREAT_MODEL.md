# Threat model

The pipeline downloads third-party benchmark metadata and publishes generated
HTML/JSON.

Risks include malicious or unexpectedly large source responses, source-schema
drift, poisoned model names/URLs, accidental credential exposure, and
redistribution of content that the project is not licensed to publish.

Controls:

- HTTPS and an explicit source allowlist;
- timeouts and maximum response sizes;
- JSON schema/type validation and HTML escaping;
- no arbitrary URL fetching from source data;
- no secrets in fixtures or generated artifacts;
- source license and attribution gates before publication;
- link-only mode for sources without explicit redistribution permission.
