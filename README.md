# Reddita (Browser Guarded fork)

> **Why this fork exists:** Upstream Reddita's default browser mode let pages make *any* GET request — including to non-Reddit sites and local-network addresses — and only checked the final URL after navigation. This fork closes that gap while keeping everything else the same.
>
> **What changed:** Every browser request, including redirect hops, is checked *before* it's sent. Only GET over HTTPS to Reddit and its asset domains is allowed; private/local addresses, POSTs, popups, service workers, WebSockets and downloads are blocked. Browser cleanup now also runs when errors occur, and Python dependencies are hash-pinned.
>
> **Why it's better:** Same Chromium browser, JavaScript, persistent profile and `reddita` commands as the original — with a much tighter network boundary and 14 tests (including real-Chromium blocking tests). It's targeted hardening, not a complete sandbox; see [SECURITY-REVIEW.md](SECURITY-REVIEW.md).
>
> Forked from [iamalwayskay/Reddita](https://github.com/iamalwayskay/Reddita) at `94d6787`. MIT licensed.


Compatibility-focused hardening fork of iamalwayskay/Reddita commit
94d6787af774a78b789ab22207e4de9f464eead0. This is NOT the earlier browser-free
Reddita Safe build. It retains the original Chromium/Patchright acquisition,
JavaScript, persistent unauthenticated profile, parser, cache, CLI and Python API.
MIT license retained. This is not an official upstream release.

## What changed, narrowly

- Native Chromium networking stays native; requests are not replaced with Python HTTP.
- CDP Fetch pauses requests at request stage, including redirect hops, before deciding
  whether to continue them. Off-page navigations are checked before sending them.
- Only GET over HTTPS to exact old.reddit.com/www.reddit.com document origins and
  Reddit-owned asset families redditstatic.com, redditmedia.com and redd.it is allowed.
- Documents must match the requested operation/page. Asset subdomains are permitted
  only at proper hostname-label boundaries (not lookalikes like redditstatic.com.evil.test).
- Requests to private/local DNS answers, non-approved domains, credentials in URLs and
  alternate ports are refused. Chromium keeps its own TLS stack and DNS resolution.
- Context-level request guarding covers popup initial requests; extra pages are closed.
- Service workers, WebSockets and downloads are disabled to avoid secondary paths.
- Request-count limits are now enforced in the native guard. Cleanup runs on errors too.

This is targeted application hardening, NOT a complete browser/network sandbox.
Read SECURITY-REVIEW.md for limits. An external dependency is still trusted code.

## Compatibility status

All five operations passed synthetic-HTML tests through actual persistent Chromium.
JavaScript execution and original CLI JSON behavior were retained in tests. External,
local-network and POST attempts plus a redirect were blocked in real Chromium tests.
14 tests passed on Linux/Python 3.12.

Live checks here could not establish parity: upstream returned HTTP 403 for about/search;
the guarded build refused this environment's private DNS address before connecting.
No DNS override or bypass was used. Live Reddit success is NOT verified. The asset
allowlist/service-worker policy may require a reviewed adjustment if Reddit changes
its infrastructure. Do not automatically allow arbitrary hosts just to make it work.

## Install with Codex

Clone this repository (`git clone https://github.com/diividen/Reddita.git`) into a new folder, open it in Codex and say:

> Read README.md, AGENTS.md and CODEX-SETUP.md, then follow CODEX-SETUP.md.
> This is the browser-based guarded version. Keep Chromium, JavaScript, native browser
> networking and the original commands. Do not replace it with a browser-free scraper.

## Manual installation (macOS/Linux, Python 3.12+)

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
patchright install chromium
python -m unittest discover -s tests -v
```

Do not use sudo/admin. If Chromium reports missing system libraries, stop and review
those requirements rather than auto-running an administrator install. requirements.lock
covers Python wheels; Patchright's browser downloads are separate and trusted through
its standard installer. If no matching wheel exists, stop rather than disabling hashes.
Do not install this into the same virtual environment as the earlier browser-free fork.

Windows: use WSL2 Ubuntu with Python 3.12+ and a project under your Linux home directory.
Run Codex in that same WSL environment. Native Windows is not supported due to the
original Unix filesystem APIs. WSL is not a disposable VM security boundary.

## Same commands as the original

```sh
.venv/bin/reddita search "Shopify marketing" 10 --json
.venv/bin/reddita sub python 15 --new --json
.venv/bin/reddita subsearch LocalLLaMA "quantization" 20 --top --json
.venv/bin/reddita about python --json
```

Thread example (replace the placeholder with a real public Reddit URL):

```sh
.venv/bin/reddita thread "PASTE_REAL_REDDIT_THREAD_URL" 25 --json
```

Add --fresh to bypass the six-hour cache. Results can be partial; check stderr and
exit status. The managed unauthenticated profile remains
~/.local/share/reddita/browser-profile/ and cache remains ~/.cache/reddita/.
Do not import personal profiles or log into the managed profile. Updating this fork
is manual; it never auto-downloads upstream changes.
