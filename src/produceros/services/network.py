"""LAN interface detection and QR code generation for LAN-mode pairing
(spec sections 18-19). Never binds to or advertises a public interface."""

from __future__ import annotations

import base64
import io
import ipaddress
import socket

import qrcode


def detect_private_ipv4() -> str | None:
    """Best-effort detection of this machine's private LAN address.

    Refuses loopback and anything that isn't in a private range (RFC
    1918), so ProducerOS never accidentally advertises a public address
    for LAN mode.
    """
    candidates: set[str] = set()

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            candidates.add(info[4][0])
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))
            candidates.add(probe.getsockname()[0])
    except OSError:
        pass

    for candidate in candidates:
        try:
            addr = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if addr.is_private and not addr.is_loopback and not addr.is_link_local:
            return str(addr)
    return None


def qr_code_data_uri(data: str) -> str:
    """Render a QR code for ``data`` as a base64 PNG data: URI, entirely
    locally -- no external QR-generation service."""
    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
