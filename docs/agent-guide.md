# Agent integration guide

## Choose an interface

Use the CLI when the calling agent can run commands and only needs JSON:

```bash
reddit-scraper search "QUERY" 20 --json
reddit-scraper sub SUBREDDIT 20 --new --json
reddit-scraper subsearch SUBREDDIT "QUERY" 20 --top --json
reddit-scraper thread THREAD_ID_OR_URL 50 --json
reddit-scraper about SUBREDDIT --json
```

Use the Python API when the host application needs typed capture metadata, provenance, continuation state, or custom budgets. Import only from `reddit_scraper` unless extending the package itself.

## Operational contract

1. Install the package and Chromium once with `patchright install chromium`.
2. Run unauthenticated. Do not supply browser profiles, cookies, tokens, or passwords.
3. Prefer `--json`; parse stdout only after a zero exit code.
4. Cache is enabled by default at `~/.cache/reddit-scraper/`; use `--fresh` only when current data matters.
5. Keep requests bounded. Split broad research into explicit, reviewable queries.
6. Report empty results and capture errors honestly; do not invent missing records.
7. Do not reinterpret this tool as authorization to access private content or interact with accounts.

## Common agent tasks

Research mentions of a product:

```bash
reddit-scraper search '"PRODUCT NAME"' 25 --new --json
```

Compare discussions in one community:

```bash
reddit-scraper subsearch COMMUNITY "TOPIC" 50 --top --json
```

Read a discussion and its top comments:

```bash
reddit-scraper thread THREAD_URL 100 --json
```

## Failure handling

- `invalid-locator` or `invalid-parameters`: fix the request; do not retry unchanged.
- `origin-denied`, `private-address-denied`, or `mixed-addresses-denied`: stop; the network safety boundary rejected the destination.
- `network-byte-limit` or continuation gaps: narrow the query or reduce the requested scope.
- `browser-failed`: confirm Chromium is installed, then retry once.
- `403 Blocked`, repeated Reddit errors, or empty HTML: stop and report the upstream limitation. Do not evade it; use the official authenticated API if the user has authorized credentials.

## Extending the project

Keep the CLI stable, add fixture-first tests for parser changes, and never weaken host, method, DNS, byte, or cache protections to make one page work. No feature may add authenticated actions or persistent browser state.
