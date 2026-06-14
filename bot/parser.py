"""
bot/parser.py
=============
Parse raw subscription text into individual config URIs.
Original remarks / metadata are NEVER modified.
Supports: VMess, VLESS, Trojan, Shadowsocks.
"""

from __future__ import annotations
import base64
import logging
import re
from typing import List, Optional

from config.settings import SUPPORTED_PROTOCOLS

logger = logging.getLogger(__name__)


def _try_base64_decode(text: str) -> str:
    """
    If the entire blob looks like base64, decode it.
    Otherwise return the text unchanged.
    """
    stripped = text.strip().replace("\n", "").replace("\r", "")
    # Heuristic: no protocol prefix and looks like base64
    has_protocol = any(stripped.startswith(p) for p in SUPPORTED_PROTOCOLS)
    if has_protocol:
        return text

    try:
        # Add padding if needed
        padded = stripped + "=" * (-len(stripped) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="replace")
        if any(decoded.startswith(p) for p in SUPPORTED_PROTOCOLS):
            return decoded
    except Exception:
        pass
    return text


def _detect_protocol(uri: str) -> Optional[str]:
    for proto in SUPPORTED_PROTOCOLS:
        if uri.startswith(proto):
            return proto.rstrip("://")
    return None


def extract_configs(raw_text: str, source_name: str) -> List[dict]:
    """
    Extract all valid config URIs from a raw subscription blob.

    Returns a list of dicts::
        {
            "uri":      str,   # original URI, untouched
            "protocol": str,   # vmess / vless / trojan / ss
            "source":   str,   # source name for auditing
        }
    """
    text = _try_base64_decode(raw_text)
    configs: List[dict] = []
    seen_in_batch: set[str] = set()

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        proto = _detect_protocol(line)
        if proto is None:
            continue

        # Deduplicate within the same fetch (cross-run dedup is done in DB)
        if line in seen_in_batch:
            continue
        seen_in_batch.add(line)

        configs.append({"uri": line, "protocol": proto, "source": source_name})

    logger.debug(
        "Source '%s': extracted %d configs from %d lines",
        source_name, len(configs), len(text.splitlines()),
    )
    return configs
