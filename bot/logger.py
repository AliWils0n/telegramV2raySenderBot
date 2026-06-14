"""
bot/logger.py
=============
Logging configuration for the entire project.
Call setup_logging() once at startup.
"""

from __future__ import annotations
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with a clean, timestamped format."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quiet noisy third-party loggers
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
