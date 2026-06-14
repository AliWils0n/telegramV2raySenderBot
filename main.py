"""
main.py
=======
Entry point for the V2Ray Aggregator Bot.
Orchestrates: fetch → dedup → save → send → mark-sent.
"""

from __future__ import annotations
import asyncio
import logging
import os
import sys

from bot.logger import setup_logging
from bot.fetcher import fetch_all_sources
from bot.sender import send_configs_tracked
from config.settings import DB_PATH, MAX_CONFIGS_PER_RUN
from database.db import ConfigDatabase

logger = logging.getLogger(__name__)


async def run() -> None:
    setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
    logger.info("══════════════════════════════════════════")
    logger.info("  V2Ray Aggregator Bot — starting run")
    logger.info("══════════════════════════════════════════")

    db = ConfigDatabase(DB_PATH)
    db.connect()

    try:
        # 1. Fetch all sources
        fetched = await fetch_all_sources()
        if not fetched:
            logger.warning("No configs fetched from any source.")
            return

        # 2. Filter to only new configs (not yet in DB)
        known_hashes = await db.async_get_known_hashes()
        import hashlib
        new_configs = [
            c for c in fetched
            if hashlib.sha256(c["uri"].strip().encode()).hexdigest() not in known_hashes
        ]
        logger.info(
            "New configs: %d / %d fetched (%.1f%% new)",
            len(new_configs), len(fetched),
            100 * len(new_configs) / len(fetched) if fetched else 0,
        )

        if not new_configs:
            logger.info("Nothing new — exiting cleanly.")
            return

        # 3. Persist new configs (unsent)
        saved = await db.async_save_configs(new_configs)
        logger.info("Saved %d new configs to database.", saved)

        # 4. Retrieve unsent (caps at MAX_CONFIGS_PER_RUN to avoid flood)
        unsent = await db.async_get_unsent(limit=MAX_CONFIGS_PER_RUN)
        logger.info("Sending %d configs to Telegram …", len(unsent))

        # 5. Send to Telegram
        sent_uris = await send_configs_tracked(unsent)

        # 6. Mark delivered configs in DB
        if sent_uris:
            await db.async_mark_sent(sent_uris)

        stats = db.stats()
        logger.info(
            "Run complete — DB total: %d | sent: %d | pending: %d",
            stats["total"], stats["sent"], stats["unsent"],
        )

    except Exception as exc:
        logger.exception("Fatal error during run: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run())
