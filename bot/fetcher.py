"""
bot/fetcher.py
==============
Async HTTP fetcher for all source types.
Handles retries, timeouts, and base64-encoded subscription blobs.
"""

from __future__ import annotations
import asyncio
import logging
from typing import List

import aiohttp

from config.settings import (
    HTTP_MAX_RETRIES,
    HTTP_RETRY_DELAY,
    HTTP_TIMEOUT,
    GITHUB_REPO_SOURCES,
    RAW_URL_SOURCES,
    GithubRepoSource,
    RawURLSource,
)
from bot.parser import extract_configs

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "V2RayAggregatorBot/1.0 (aggregator; +https://github.com)",
    "Accept": "text/plain, */*",
}


async def _fetch_url(
    session: aiohttp.ClientSession,
    url: str,
    retries: int = HTTP_MAX_RETRIES,
) -> str | None:
    """Fetch *url* with automatic retry on transient errors."""
    for attempt in range(1, retries + 1):
        try:
            async with session.get(
                url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    return await resp.text(encoding="utf-8", errors="replace")
                logger.warning("HTTP %s for %s (attempt %d)", resp.status, url, attempt)
        except asyncio.TimeoutError:
            logger.warning("Timeout fetching %s (attempt %d)", url, attempt)
        except aiohttp.ClientError as exc:
            logger.warning("Client error fetching %s: %s (attempt %d)", url, exc, attempt)

        if attempt < retries:
            await asyncio.sleep(HTTP_RETRY_DELAY * attempt)

    logger.error("Giving up on %s after %d attempts", url, retries)
    return None


async def fetch_raw_source(
    session: aiohttp.ClientSession,
    source: RawURLSource,
) -> List[dict]:
    """Fetch a single RawURLSource and return parsed configs."""
    if not source.enabled:
        return []
    logger.info("Fetching raw source: %s", source.name)
    text = await _fetch_url(session, source.url)
    if text is None:
        return []
    return extract_configs(text, source.name)


async def fetch_github_repo_source(
    session: aiohttp.ClientSession,
    source: GithubRepoSource,
) -> List[dict]:
    """Fetch all paths in a GithubRepoSource concurrently."""
    if not source.enabled:
        return []
    logger.info("Fetching GitHub repo source: %s (%d paths)", source.name, len(source.paths))

    tasks = [
        _fetch_url(session, source.raw_url(path))
        for path in source.paths
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    configs: List[dict] = []
    for path, result in zip(source.paths, results):
        if isinstance(result, Exception):
            logger.error("Error fetching %s/%s: %s", source.name, path, result)
            continue
        if result is None:
            continue
        configs.extend(extract_configs(result, f"{source.name}:{path}"))
    return configs


async def fetch_all_sources() -> List[dict]:
    """
    Fetch every enabled source (raw URLs + GitHub repos) concurrently.
    Returns deduplicated list of config dicts.
    """
    connector = aiohttp.TCPConnector(limit=10, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks: list = []

        for src in RAW_URL_SOURCES:
            tasks.append(fetch_raw_source(session, src))
        for src in GITHUB_REPO_SOURCES:
            tasks.append(fetch_github_repo_source(session, src))

        batches = await asyncio.gather(*tasks, return_exceptions=True)

    all_configs: List[dict] = []
    seen_uris: set[str] = set()

    for batch in batches:
        if isinstance(batch, Exception):
            logger.error("Source batch failed: %s", batch)
            continue
        for cfg in batch:
            if cfg["uri"] not in seen_uris:
                seen_uris.add(cfg["uri"])
                all_configs.append(cfg)

    logger.info("Total unique configs fetched across all sources: %d", len(all_configs))
    return all_configs
