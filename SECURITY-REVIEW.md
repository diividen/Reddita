# Security and compatibility notes — October 22, 2026

This build corrects an over-broad earlier redesign. The original browser acquisition,
CLI commands, parsing, managed profile and six-hour cache remain. browser_guard.py
adds request-stage checks; scraper.py installs the guard, disables service workers/
downloads, intercepts WebSockets, closes extra pages and ensures cleanup on exceptions.
The original any-GET handler is removed. Requirements are version/hash pinned separately.

## Verified

- Original source commit: 94d6787af774a78b789ab22207e4de9f464eead0.
- Python 3.12.12/Linux, Patchright 1.64.2 and its Chromium installer.
- 14 passing tests, including real Chromium request interception and real persistent
  Chromium for all five operations using synthetic Reddit HTML.
- JavaScript still runs. Off-domain and local-IP GETs and same-origin POSTs are denied.
- A synthetic 302 redirect's off-domain destination was intercepted and refused.
- Existing parser/cache/CLI tests still pass, except the obsolete permissive-router
  test was replaced by tests of the new guard.
- Independent review identified popup target and cleanup gaps; context-wide fallback
  interception and finally cleanup were added in response.

## Live comparison

On this execution environment, upstream about and search both returned HTTP403.
The guarded build rejected navigation because DNS resolves the Reddit hosts to a
private address here. That is an intentional refusal, NOT a demonstrated scraping
regression on normal public DNS. However neither result establishes live compatibility.
No proxy, special DNS override, login or blocking workaround was used.

## Honest boundaries

This is not an OS firewall, full Chromium sandbox or guarantee against getting hacked.
Browser/Python/native dependency vulnerabilities and supply-chain risk remain.
The allowed asset hosts are narrow Reddit infrastructure families, not a promise that
all content from those hosts is benign. Browser JavaScript remains deliberately enabled.

Private-address DNS checks occur before continuing a request, but Chromium resolves
independently. Unlike the separate strict Python transport, native-browser mode does
NOT pin the connection IP. A DNS race/rebinding or malicious DNS change remains possible.
This is a deliberate compatibility trade-off, not a claimed complete SSRF solution.

Controls apply after guard attachment to capture traffic; browser startup/background
behavior is not an OS-level network boundary. Context-wide routing denies foreign page
requests and the CDP guard checks capture-page redirect hops. Service workers are blocked,
WebSockets closed and extra pages closed. Other browser/network mechanisms are not
formally proven isolated. For stronger isolation use a separate VM/network policy.

Native mode retains the upstream limitation that its byte budget measures captured
HTML, not every resource byte downloaded by Chromium. The request count is enforced;
there is no whole-profile disk quota. Cache accumulates over time.

A profile is private but persistent and shared with upstream at its original default
path. Never import personal cookies, sign into it or provide browser credentials.
No credentials are requested or deliberately harvested by this project's code.

Strict document navigation and approved-host rules, blocked service workers and capped
requests can expose infrastructure/compatibility differences if Reddit changes. Do not
promise identical success on every network. Fail honestly rather than weakening guards.

Python wheel hashes were obtained from PyPI metadata; hashes identify artifacts, not
prove they are benign. Browser binaries are installed separately by Patchright and are
not included in the Python wheel hash lock.
