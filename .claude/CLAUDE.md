# Reddit Scraper repository instructions

This is a standalone, read-only public Reddit research scraper.

- Preserve the public command: `reddit-scraper`.
- Preserve the supported operations: `search`, `sub`, `subsearch`, `thread`, and `about`.
- Never add credentials, cookies, login flows, browser profiles, posting, voting, messaging, or private-content access.
- Never weaken the Reddit-only HTTPS/GET boundary, DNS pinning, public-address checks, or finite budgets.
- Add local fixture tests for parser or output changes; tests must not require live Reddit.
- Keep stdout machine-readable under `--json`; diagnostics belong on stderr with a non-zero exit.
- Do not add dependencies unless the existing standard library, Pydantic, Beautiful Soup, lxml, or Patchright cannot solve the problem.
- Run `python -m unittest discover -s tests -v` before claiming completion.

Start with `README.md`, then `docs/agent-guide.md`. The package lives in `src/reddit_scraper/`.
