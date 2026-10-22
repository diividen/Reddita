"""Targeted Chromium request-stage guard; keeps browser networking and JavaScript.

CDP Fetch pauses every request including redirect hops, unlike a handler that only
checks a completed navigation. This is application hardening, not an OS sandbox.
"""
from urllib.parse import urlsplit
import ipaddress
import socket
import unicodedata

from .scraper import RedditCaptureError, _validate_page_url

RESOURCE_ROOTS = frozenset({'redditstatic.com', 'redditmedia.com', 'redd.it'})
DOCUMENT_HOSTS = frozenset({'old.reddit.com', 'www.reddit.com'})


def approved_resource_url(url: str) -> bool:
    if len(url) > 8192 or any(unicodedata.category(c) == 'Cc' for c in url):
        return False
    try:
        p = urlsplit(url)
        h = p.hostname or ''
        return (p.scheme == 'https' and p.username is None and p.password is None
                and p.port in {None, 443} and not p.fragment
                and (h in DOCUMENT_HOSTS or any(h == root or h.endswith('.'+root)
                                               for root in RESOURCE_ROOTS)))
    except ValueError:
        return False


def public_dns(host: str) -> bool:
    """Preflight public addresses; Chromium still performs its own DNS resolution.

Only fixed Reddit-owned host families are allowed. This check is NOT IP pinning
and cannot eliminate a DNS rebinding race; see SECURITY-REVIEW.md.
"""
    try:
        rows = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addresses = [ipaddress.ip_address(row[4][0].split('%',1)[0]) for row in rows]
        return bool(addresses) and all(a.is_global and not a.is_multicast
                                      and not a.is_reserved for a in addresses)
    except (OSError, ValueError, IndexError):
        return False


class BrowserGuard:
    def __init__(self, operation, identity, initial_url, *, max_requests=100,
                 resolver=public_dns, fixture=None):
        self.operation, self.identity, self.initial_url = operation, identity, initial_url
        self.max_requests, self.resolver, self.fixture = max_requests, resolver, fixture
        self.requests = 0
        self.blocked = []
        self.sessions = []
        self.navigation_denied = False

    def permits(self, method, url, *, document=False, count=True):
        if count:
            self.requests += 1
        if self.requests > self.max_requests or method != 'GET' or not approved_resource_url(url):
            return False
        if document:
            try:
                _validate_page_url(self.operation, self.identity, self.initial_url, url)
            except RedditCaptureError:
                return False
        return self.resolver(urlsplit(url).hostname)

    def attach(self, context, page):
        # Context-level fallback covers new popup targets before they can receive
        # their own CDP session. Redirect hops on the capture page also pass CDP.
        def context_route(route):
            req = route.request
            try:
                foreign_page = req.frame.page != page
            except Exception:
                foreign_page = False  # Worker requests still undergo URL/method/DNS checks.
            if foreign_page or not self.permits(req.method, req.url,
                    document=req.is_navigation_request(), count=False):
                self.blocked.append((req.method, req.url))
                if not foreign_page and req.is_navigation_request():
                    self.navigation_denied = True
                route.abort()
            else:
                route.continue_()
        context.route('**/*', context_route)
        for existing in list(context.pages):
            if existing != page:
                existing.close()
        if not hasattr(context, 'route_web_socket'):
            raise RedditCaptureError('guard-unavailable', 'Context WebSocket interception is required')
        context.route_web_socket('**/*', lambda ws: ws.close())
        session = context.new_cdp_session(page)
        self.sessions.append(session)
        def paused(event):
            request = event['request']
            document = event.get('resourceType') == 'Document'
            allowed = self.permits(request['method'], request['url'], document=document)
            rid = event['requestId']
            if not allowed:
                self.blocked.append((request['method'], request['url']))
                if document:
                    self.navigation_denied = True
                session.send('Fetch.failRequest', {'requestId': rid, 'errorReason': 'BlockedByClient'})
            elif self.fixture is not None:
                self.fixture(session, event)
            else:
                session.send('Fetch.continueRequest', {'requestId': rid})
        session.on('Fetch.requestPaused', paused)
        session.send('Fetch.enable', {'patterns': [{'urlPattern':'*', 'requestStage':'Request'}]})
        # No downloads or unsolicited new pages. Browser contexts can otherwise
        # allow state-changing WebSocket traffic outside ordinary HTTP methods.
        page.on('download', lambda download: download.cancel())
        if not hasattr(page, 'route_web_socket'):
            raise RedditCaptureError('guard-unavailable', 'WebSocket interception is required')
        page.route_web_socket('**/*', lambda ws: ws.close())

    def check_navigation(self):
        if self.navigation_denied:
            raise RedditCaptureError('redirect-denied', 'Browser guard blocked a navigation before sending it')
