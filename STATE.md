# State

Reddita is a standalone public repository derived from the original archived Reddit scraper, with personal paths and identifiers removed.

The CLI preserves the original working acquisition model: an unauthenticated persistent browser profile, human-paced pagination, old-Reddit HTML parsing, a six-hour private cache, and JSON output. The profile is Reddita-owned and never imports personal cookies or credentials. Browser writes are blocked.

Verified on 2026-10-22:

- all 10 unit tests pass;
- package compilation and dependency checks pass;
- a fresh live `about python --json` capture succeeds;
- the following cached capture returns the same record.

Current upstream constraint: Reddit redirects some logged-out listing, search, and thread routes to its login page on this network. Reddita rejects that redirect and returns an explicit error rather than a misleading empty result.
