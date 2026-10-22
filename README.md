# Reddita

A read-only Reddit research tool for humans and AI agents. It searches public posts, reads subreddit listings and threads, and returns community metadata without an API key, Reddit app, login, or persistent browser profile.

It is deliberately bounded: HTTPS only, Reddit hosts only, GET requests only, finite request/byte/record limits, and no posting, voting, messaging, authentication, or private content.

## Install

Requires Python 3.12+.

```bash
git clone <repository-url>
cd reddita
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
patchright install chromium
```

## Use

```bash
reddita search "local AI tools" 10
reddita sub python 15 --new
reddita subsearch LocalLLaMA "quantization" 20 --top
reddita thread https://www.reddit.com/r/python/comments/abc123/example/ 25
reddita about python
```

Add `--json` for machine-readable output. Add `--fresh` to bypass the private six-hour cache.

```bash
reddita search "open source OCR" 10 --json > results.json
```

The command exits non-zero on invalid input, a denied network boundary, a browser failure, or an incomplete empty response. Reddit can change its HTML, return `403 Blocked`, or rate-limit unauthenticated requests by network/IP; the tool reports that rather than bypassing it. Treat captures as research evidence, not a guaranteed API.

## Give it to Claude, GPT, or another coding agent

Share the repository URL and this prompt:

> Install this repository following its README. Use `reddita ... --json` for public Reddit research. Never add credentials, cookies, login automation, posting, voting, or private-content access. Preserve the request and byte limits. When integrating it, prefer the CLI for subprocess use or the documented Python API for in-process use.

The repository also includes [docs/agent-guide.md](docs/agent-guide.md) and an `AGENTS.md` instruction file that coding agents discover automatically.

## Python API

```python
import json

from reddita import SourceBudgets, SourceRequest, acquire_reddit

request = SourceRequest(
    source="reddit",
    operation="search",
    locator="local AI tools",
    parameters_json=json.dumps({
        "pageSize": 10,
        "maxComments": 100,
        "sort": "relevance",
    }),
    max_records=10,
    max_pages=1,
)

capture = acquire_reddit(
    request,
    budgets=SourceBudgets(),
    settings_digest="0" * 64,
)

for record in capture.result.records:
    print(json.loads(record.data_json))
```

`settings_digest` identifies the caller's effective settings for cache correctness. Use a stable SHA-256 hex digest in production.

## Output model

- `search`, `sub`, and `subsearch` return post records.
- `thread` returns one thread record followed by bounded comment records.
- `about` returns one community record.
- Every record carries a stable ID, source index, canonical source URL, and canonical JSON payload.
- Capture metadata records completeness, pages, typed gaps, continuation state, and acquisition time.

## Safety and scope

- Public `old.reddit.com` and `www.reddit.com` pages only.
- Fresh JavaScript-disabled browser context for every uncached run.
- Browser requests are intercepted and fulfilled through a DNS-pinned public HTTPS transport.
- Private, loopback, link-local, reserved, mixed public/private, changing DNS, non-HTTPS, non-GET, credential, and off-domain routes are denied.
- Response bytes, requests, pages, records, comments, continuation state, and cache entries are bounded.
- Cache directories and files reject symlinks and unsafe permissions.

This is not an official Reddit client. If Reddit blocks public HTML from the machine running it, use Reddit's official authenticated API instead; do not add stealth, cookies, or login automation to work around the block.

Use the tool responsibly and comply with applicable laws, Reddit's terms, and community expectations.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The tests use local HTML fixtures and mocked acquisition; they do not depend on Reddit being reachable.

## License

MIT. See [LICENSE](LICENSE).
