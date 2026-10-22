"""Pinned HTTPS transport for source-specific public-reference capture."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import http.client
import ipaddress
import socket
from typing import Callable, Iterable
from urllib.parse import urlsplit, urlunsplit

from .security import classify_literal_host, is_localhost_host, normalize_capture_url


class PublicTransportError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ResolvedPublicDestination:
    url: str
    host: str
    port: int
    addresses: frozenset[str]
    pinned_ip: str


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to one validated address while authenticating the original host."""

    def __init__(self, host: str, *, pinned_ip: str, port: int = 443, **kwargs) -> None:
        super().__init__(host, port=port, **kwargs)
        self.pinned_ip = pinned_ip

    def connect(self) -> None:
        try:
            self.sock = self._create_connection(
                (self.pinned_ip, self.port), self.timeout, self.source_address,
            )
            if self._tunnel_host:
                raise PublicTransportError("proxy-denied", "HTTP tunnels are denied")
            self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)
            peer = ipaddress.ip_address(self.sock.getpeername()[0].split("%", 1)[0])
            if peer != ipaddress.ip_address(self.pinned_ip):
                raise PublicTransportError(
                    "peer-address-mismatch", "HTTPS peer did not match its pinned address"
                )
        except PublicTransportError:
            if self.sock is not None:
                self.sock.close()
                self.sock = None
            raise


class PublicHttpsBoundary:
    """Require globally routable stable DNS answers and pin the selected address."""

    def __init__(self, *, allowed_hosts: Iterable[str],
                 resolver: Callable[..., list] | None = None,
                 connection_type=PinnedHTTPSConnection) -> None:
        self.allowed_hosts = frozenset(host.casefold() for host in allowed_hosts)
        self.resolver = resolver or socket.getaddrinfo
        self.connection_type = connection_type
        self._origins: dict[tuple[str, int], tuple[frozenset[str], str]] = {}

    def resolve(self, value: str) -> ResolvedPublicDestination:
        try:
            normalized = normalize_capture_url(value, reject_fragment=True)
            parsed = urlsplit(normalized)
            host = (parsed.hostname or "").encode("idna").decode("ascii").casefold()
            if (parsed.scheme != "https" or host not in self.allowed_hosts
                    or parsed.username is not None or parsed.password is not None
                    or parsed.port not in {None, 443} or is_localhost_host(host)):
                raise PublicTransportError(
                    "origin-denied", "public capture requires an allowed HTTPS origin"
                )
            literal = classify_literal_host(host)
            if literal is not None:
                address, legacy = literal
                if legacy:
                    raise PublicTransportError(
                        "private-address-denied", "noncanonical numeric hosts are denied"
                    )
                raw_addresses = {address}
            else:
                rows = self.resolver(host, 443, type=socket.SOCK_STREAM)
                raw_addresses = {
                    ipaddress.ip_address(row[4][0].split("%", 1)[0]) for row in rows
                }
        except PublicTransportError:
            raise
        except (OSError, UnicodeError, ValueError, IndexError, TypeError):
            raise PublicTransportError("dns-failed", "public host could not be resolved") from None
        if not raw_addresses:
            raise PublicTransportError("dns-failed", "public host returned no addresses")
        public_unicast = {_is_public_unicast(address) for address in raw_addresses}
        if public_unicast != {True}:
            contains_non_unicast = any(
                address.is_multicast or address.is_unspecified
                for address in raw_addresses
            )
            raise PublicTransportError(
                ("mixed-addresses-denied" if len(public_unicast) > 1
                 else "non-unicast-address-denied" if contains_non_unicast
                 else "private-address-denied"),
                "public capture requires globally routable unicast addresses",
            )
        addresses = frozenset(str(address) for address in raw_addresses)
        selected = str(sorted(
            raw_addresses, key=lambda item: (item.version != 4, str(item))
        )[0])
        origin = (host, 443)
        previous = self._origins.get(origin)
        if previous is not None and previous[0] != addresses:
            raise PublicTransportError(
                "address-change-denied", "public origin addresses changed after validation"
            )
        self._origins.setdefault(origin, (addresses, selected))
        return ResolvedPublicDestination(
            url=normalized, host=host, port=443, addresses=addresses,
            pinned_ip=self._origins[origin][1],
        )

    @contextmanager
    def open(self, value: str, *, headers: dict[str, str], timeout_seconds: int):
        destination = self.resolve(value)
        connection = self.connection_type(
            destination.host, port=destination.port, pinned_ip=destination.pinned_ip,
            timeout=timeout_seconds,
        )
        response = None
        try:
            parsed = urlsplit(destination.url)
            target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
            connection.request("GET", target, headers=headers)
            response = connection.getresponse()
            yield response
        finally:
            if response is not None:
                response.close()
            connection.close()


def _is_public_unicast(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Accept only ordinary public unicast destinations, never special-use ranges."""
    return (
        address.is_global
        and not address.is_multicast
        and not address.is_unspecified
        and not address.is_reserved
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_private
        and not getattr(address, "is_site_local", False)
    )
