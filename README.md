# Reddita

A read-only Reddit research tool for humans and AI agents. It searches public posts, reads subreddit listings and threads, and returns community metadata without an API key, Reddit app, or login. It carries forward the original scraper's private persistent browser profile, polite pacing, and six-hour cache.

It is deliberately read-only: the browser permits GET requests and aborts state-changing methods. Main navigation is HTTPS and must end on the requested Reddit page. Posting, voting, messaging, authentication, and private content are unsupported.

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

> Install this repository following its README. Use `reddita ... --json` for public Reddit research. Let Reddita manage its own unauthenticated browser profile; never import a personal profile or add credentials, login automation, posting, voting, or private-content access. When integrating it, prefer the CLI for subprocess use or the documented Python API for in-process use.

The repository also includes [docs/agent-guide.md](docs/agent-guide.md) and an `AGENTS.md` instruction file that coding agents discover automatically.

## Python API

```python
import json
from pathlib import Path

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
    profile_root=Path.home() / ".local" / "share" / "reddita" / "browser-profile",
    native_transport=True,
    allow_stealth=True,
)

for record in capture.result.records:
    print(json.loads(record.data_json))
```

`settings_digest` identifies the caller's effective settings for cache correctness. Use a stable SHA-256 hex digest in production. The CLI is the recommended interface because it creates and validates the private profile and cache directories automatically.

## Output model

- `search`, `sub`, and `subsearch` return post records.
- `thread` returns one thread record followed by bounded comment records.
- `about` returns one community record.
- Every record carries a stable ID, source index, canonical source URL, and canonical JSON payload.
- Capture metadata records completeness, pages, typed gaps, continuation state, and acquisition time.

## Safety and scope

- Main navigation is restricted to the requested public `old.reddit.com` or `www.reddit.com` page.
- The CLI reuses an unauthenticated profile at `~/.local/share/reddita/browser-profile/`; profile and cache directories are private and reject symlinks.
- The browser may load GET resources referenced by Reddit, but aborts POST and every other state-changing method.
- Captured HTML, pages, records, comments, continuation state, and cache entries are bounded.
- Cache directories and files reject symlinks and unsafe permissions.

This is not an official Reddit client. Reddit currently redirects some logged-out old-Reddit listing/search/thread routes to login on some networks. Reddita reports that explicitly instead of returning a fake empty result. If that happens, use Reddit's official authenticated API; do not import a logged-in personal profile.

Use the tool responsibly and comply with applicable laws, Reddit's terms, and community expectations.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The tests use local HTML fixtures and mocked acquisition; they do not depend on Reddit being reachable.

## License

MIT. See [LICENSE](LICENSE).
