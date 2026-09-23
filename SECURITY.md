# Security

Please report security issues privately through
[GitHub's private vulnerability reporting form](https://github.com/aknochow/modelagency/security/advisories/new)
before public disclosure. Do not open a public issue for an unpatched
vulnerability, and do not include credentials, private benchmark data, or
sensitive CI logs in a report.

Reports should include the affected revision, a minimal reproduction, impact,
and any suggested mitigation. The maintainer will acknowledge reports as
soon as practical, coordinate a fix and disclosure timeline, and credit
reporters who opt in. Private vulnerability reporting must be enabled in the
repository settings before the project is made public.

The project intentionally has no model credentials and no inference calls.
Future source fetchers must use HTTPS, bounded response sizes, timeouts,
allowlisted URLs, and schema validation.
