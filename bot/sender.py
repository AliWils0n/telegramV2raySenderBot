"""
bot/sender.py
=============
Sends config batches to Telegram.

- Original config URIs are forwarded UNCHANGED (remarks fully preserved).
- A footer (channel attribution) is appended to the Telegram message TEXT only.
- Respects Telegram's 4096-character limit by splitting into multiple messages.
"""

from __future__ import annotations
import asyncio
import logging
from typing import List

import aiohttp

from config.settings import (
    BOT_TOKEN,
    CHAT_ID,
    MAX_MESSAGE_LENGTH,
    MESSAGE_FOOTER,
    MESSAGE_HEADER,
    SEND_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)
TELEGRAM_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"


def _split_into_batches(configs: List[dict]) -> List[List[str]]:
    """
    Group config URIs into batches so each rendered Telegram message
    stays within MAX_MESSAGE_LENGTH characters.
    """
    # Calculate how much room the fixed parts consume
    fixed_len = len(MESSAGE_HEADER) + len(MESSAGE_FOOTER) + 4   # 4 = two '\n\n'
    max_body  = MAX_MESSAGE_LENGTH - fixed_len

    batches:      List[List[str]] = []
    current:      List[str]       = []
    current_len:  int             = 0

    for cfg in configs:
        line     = cfg["uri"]
        line_len = len(line) + 1  # +1 for the '\n' separator

        if current and current_len + line_len > max_body:
            batches.append(current)
            current     = []
            current_len = 0

        current.append(line)
        current_len += line_len

    if current:
        batches.append(current)

    return batches


def _format_message(uris: List[str]) -> str:
    """Compose the final Telegram message text for one batch."""
    body = "\n".join(uris)
    return f"{MESSAGE_HEADER}\n\n{body}{MESSAGE_FOOTER}"


async def send_configs_tracked(configs: List[dict]) -> List[str]:
    """
    Send all *configs* to Telegram.

    Returns the URIs that were successfully delivered so the caller can
    mark them as sent in the database.  Batches that fail are NOT marked,
    so they will be retried on the next run.
    """
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("BOT_TOKEN or CHAT_ID not set — skipping Telegram delivery.")
        return []

    if not configs:
        logger.info("No new configs to send.")
        return []

    batches        = _split_into_batches(configs)
    api_url        = TELEGRAM_SEND_URL.format(token=BOT_TOKEN)
    sent_uris: List[str] = []

    # Build index: batch_index → [uri, uri, …]
    batch_uri_map = _split_into_batches(configs)   # same split, list of uri lists

    logger.info("Sending %d configs in %d Telegram message(s).", len(configs), len(batches))

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for idx, uris in enumerate(batch_uri_map, start=1):
            text    = _format_message(uris)
            payload = {
                "chat_id":                  CHAT_ID,
                "text":                     text,
                "disable_web_page_preview": True,
            }

            try:
                async with session.post(
                    api_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()

                if data.get("ok"):
                    logger.info(
                        "✅ Batch %d/%d sent — %d configs, %d chars.",
                        idx, len(batch_uri_map), len(uris), len(text),
                    )
                    sent_uris.extend(uris)
                else:
                    logger.error(
                        "❌ Telegram rejected batch %d/%d: %s",
                        idx, len(batch_uri_map), data.get("description", data),
                    )

            except asyncio.TimeoutError:
                logger.error("Timeout on batch %d/%d — will retry next run.", idx, len(batch_uri_map))
            except aiohttp.ClientError as exc:
                logger.error("Network error on batch %d/%d: %s", idx, len(batch_uri_map), exc)

            # Rate-limit protection
            if idx < len(batch_uri_map):
                await asyncio.sleep(SEND_DELAY_SECONDS)

    logger.info(
        "Telegram delivery complete: %d/%d configs sent successfully.",
        len(sent_uris), len(configs),
    )
    return sent_uris
