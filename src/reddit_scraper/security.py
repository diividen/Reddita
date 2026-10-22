"""Minimal URL checks used by the pinned public HTTPS transport."""

from __future__ import annotations

import ipaddress
import re
import socket
import unicodedata
from urllib.parse import urldefrag, urlsplit


MAX_CAPTURE_URL_LENGTH = 4096
_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_LEGACY_NUMERIC_HOST = re.compile(
    r"(?i)^(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+)){0,3}$"
)


def is_localhost_host(value: str) -> bool:
    normalized = value.rstrip(".").casefold()
    return normalized == "localhost" or normalized.endswith(".localhost")


def classify_literal_host(
    value: str,
) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, bool] | None:
    normalized = value.rstrip(".")
    try:
        return ipaddress.ip_address(normalized), False
    except ValueError:
        pass
    if not _LEGACY_NUMERIC_HOST.fullmatch(normalized):
        return None
    try:
        packed = socket.inet_aton(normalized)
    except OSError:
        return None
    return ipaddress.IPv4Address(packed), True


def normalize_capture_url(value: str, *, reject_fragment: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_CAPTURE_URL_LENGTH:
        raise ValueError("capture URL length is invalid")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError("capture URL contains a control character")
    try:
        parsed = urlsplit(value)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("capture URL must use HTTP(S)")
        if parsed.hostname is None or parsed.username is not None or parsed.password is not None:
            raise ValueError("capture URL authority is invalid")
        _ = parsed.port
        if parsed.fragment and reject_fragment:
            raise ValueError("capture URL cannot contain a fragment")
        host = parsed.hostname
        try:
            ipaddress.ip_address(host.split("%", 1)[0])
            if "%" in host:
                raise ValueError("scoped addresses are not capture hosts")
        except ValueError as address_error:
            if "%" in host:
                raise
            ascii_host = host.encode("idna").decode("ascii")
            rootless = ascii_host[:-1] if ascii_host.endswith(".") else ascii_host
            if (not rootless or len(rootless) > 253
                    or any(not _HOST_LABEL.fullmatch(label) for label in rootless.split("."))):
                raise ValueError("capture host is invalid") from address_error
    except (UnicodeError, ValueError) as error:
        raise ValueError("capture URL is invalid") from error
    return urldefrag(value)[0]
