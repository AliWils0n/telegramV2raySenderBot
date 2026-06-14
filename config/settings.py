"""
config/settings.py
==================
Central configuration for the V2Ray Aggregator Bot.
Add / remove sources here without touching any other file.
All secrets come from environment variables.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List

# ── Telegram credentials (set as GitHub Actions secrets) ──────────────────────
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
CHAT_ID: str   = os.environ.get("CHAT_ID", "")

# ── Footer appended below every outgoing message ──────────────────────────────
# Original config remarks are NEVER modified. This text is only added to the
# Telegram message body, not to the config URI itself.
MESSAGE_FOOTER: str = (
    "\n━━━━━━━━━━━━\n"
    "وی پی ان آیپی ثابت ارزان قیمت\n"
    "@zirolost"
)
MESSAGE_HEADER: str = "📡 کانفیگ‌های جدید یافت شد"

# ── Telegram limits ───────────────────────────────────────────────────────────
MAX_MESSAGE_LENGTH: int  = 4096
SEND_DELAY_SECONDS: float = 1.5   # polite gap between API calls

# ── Persistence ───────────────────────────────────────────────────────────────
DB_PATH: str = os.environ.get("DB_PATH", "database/configs.db")

# ── HTTP ──────────────────────────────────────────────────────────────────────
HTTP_TIMEOUT: int        = 30
HTTP_MAX_RETRIES: int    = 3
HTTP_RETRY_DELAY: float  = 2.0

# ── Supported protocol prefixes ───────────────────────────────────────────────
SUPPORTED_PROTOCOLS = ("vmess://", "vless://", "trojan://", "ss://")

# ── Max new configs to send per run (avoid Telegram flood) ───────────────────
MAX_CONFIGS_PER_RUN: int = 50


# ──────────────────────────────────────────────────────────────────────────────
# Source dataclasses
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RawURLSource:
    """
    A public URL returning a plain-text or base64-encoded subscription list.
    One config URI per line after optional base64 decode.
    """
    name: str
    url: str
    enabled: bool = True


@dataclass
class GithubRepoSource:
    """
    A GitHub repository containing subscription text files.
    Each path is fetched via raw.githubusercontent.com.
    """
    name: str
    owner: str
    repo: str
    branch: str = "main"
    paths: List[str] = field(default_factory=list)
    enabled: bool = True

    def raw_url(self, path: str) -> str:
        return (
            f"https://raw.githubusercontent.com/"
            f"{self.owner}/{self.repo}/{self.branch}/{path}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# ★  RAW URL SOURCES  — add new rows here freely
# ──────────────────────────────────────────────────────────────────────────────
RAW_URL_SOURCES: List[RawURLSource] = [
    RawURLSource(
        name="barry-far-all",
        url="https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    ),
    RawURLSource(
        name="mahdibland-vmess",
        url="https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/vmess.txt",
    ),
    RawURLSource(
        name="mahdibland-vless",
        url="https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/vless.txt",
    ),
    RawURLSource(
        name="mahdibland-trojan",
        url="https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/trojan.txt",
    ),
    RawURLSource(
        name="mahdibland-ss",
        url="https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/shadowsocks.txt",
    ),
    RawURLSource(
        name="freefq-free",
        url="https://raw.githubusercontent.com/freefq/free/master/v2",
    ),
    RawURLSource(
        name="peasoft-NoMoreWalls",
        url="https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    ),
    RawURLSource(
        name="Pawdroid-free-servers",
        url="https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    ),
    RawURLSource(
        name="mfuu-v2ray",
        url="https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    ),
    RawURLSource(
        name="ermaozi-v2ray",
        url="https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    ),
    RawURLSource(
        name="aiboboxx-v2rayfree",
        url="https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# ★  GITHUB REPO SOURCES  — add new repos here freely
# ──────────────────────────────────────────────────────────────────────────────
GITHUB_REPO_SOURCES: List[GithubRepoSource] = [
    GithubRepoSource(
        name="barry-far-repo",
        owner="barry-far",
        repo="V2ray-Configs",
        branch="main",
        paths=[
            "Configs/Trojan_Configs.txt",
            "Configs/Vless_Configs.txt",
            "Configs/Vmess_Configs.txt",
            "Configs/ShadowSocks_Configs.txt",
        ],
    ),
    GithubRepoSource(
        name="mahdibland-aggregator",
        owner="mahdibland",
        repo="V2RayAggregator",
        branch="master",
        paths=[
            "sub/splitted/vmess.txt",
            "sub/splitted/vless.txt",
            "sub/splitted/trojan.txt",
            "sub/splitted/shadowsocks.txt",
        ],
    ),
]
