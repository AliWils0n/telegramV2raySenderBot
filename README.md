# V2Ray Aggregator Bot 📡

A production-ready Telegram bot that monitors public V2Ray/Xray subscription sources,
detects new configs, and forwards them to your Telegram channel — **fully automated
on GitHub Actions with no VPS required**.

Original config remarks and metadata are **never modified**. Your channel attribution
is appended as a footer to the Telegram message only.

---

## Features

- ✅ Runs every 5 minutes on free GitHub Actions runners
- ✅ Supports **VMess, VLESS, Trojan, Shadowsocks**
- ✅ Deduplication via SHA-256 hashing (SQLite database)
- ✅ Database persisted between runs via GitHub Actions cache
- ✅ Original config remarks fully preserved
- ✅ Configurable sources — add a URL in one line
- ✅ Async/concurrent fetching (aiohttp)
- ✅ Respects Telegram message length limits (batching)
- ✅ Full logging and error handling

---

## Project Structure

```
v2ray_bot/
├── .github/
│   └── workflows/
│       └── run_bot.yml        # GitHub Actions cron workflow
├── bot/
│   ├── __init__.py
│   ├── fetcher.py             # Async source fetcher
│   ├── parser.py              # Config URI extractor / base64 decoder
│   ├── sender.py              # Telegram message sender
│   └── logger.py              # Logging setup
├── config/
│   ├── __init__.py
│   └── settings.py            # ★ All sources configured here ★
├── database/
│   ├── __init__.py
│   └── db.py                  # SQLite persistence layer
├── main.py                    # Entry point
├── requirements.txt
└── README.md
```

---

## Quick Setup

### 1. Fork / clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/v2ray-aggregator-bot.git
cd v2ray-aggregator-bot
```

### 2. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the **Bot Token** you receive

### 3. Get your Channel / Group Chat ID

- For a **public channel**: use `@your_channel_username`
- For a **private channel or group**: add your bot to the channel as Admin,
  then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` after sending
  a message — look for `"chat": {"id": -100XXXXXXXXXX}`

### 4. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value                          |
|-------------|--------------------------------|
| `BOT_TOKEN` | Your Telegram bot token        |
| `CHAT_ID`   | Your channel/group ID or @name |

### 5. Enable GitHub Actions

- Go to the **Actions** tab in your repository
- Click **"I understand my workflows, go ahead and enable them"**
- The bot will run automatically every 5 minutes

### 6. Manual test run

In the **Actions** tab, select **"V2Ray Aggregator Bot"** → **"Run workflow"**.

---

## Adding New Sources

Open `config/settings.py` and add a row to either list:

### Add a raw subscription URL

```python
RAW_URL_SOURCES: List[RawURLSource] = [
    # ... existing sources ...
    RawURLSource(
        name="my-new-source",
        url="https://example.com/subscription.txt",
    ),
]
```

### Add a GitHub repository

```python
GITHUB_REPO_SOURCES: List[GithubRepoSource] = [
    # ... existing sources ...
    GithubRepoSource(
        name="some-repo",
        owner="github-user",
        repo="free-v2ray",
        branch="main",
        paths=["configs/vmess.txt", "configs/vless.txt"],
    ),
]
```

To **disable** a source without deleting it, set `enabled=False`.

---

## Environment Variables

| Variable    | Required | Default             | Description                    |
|-------------|----------|---------------------|--------------------------------|
| `BOT_TOKEN` | ✅ Yes   | —                   | Telegram bot token             |
| `CHAT_ID`   | ✅ Yes   | —                   | Target channel/group ID        |
| `DB_PATH`   | No       | `database/configs.db` | SQLite database path         |
| `LOG_LEVEL` | No       | `INFO`              | `DEBUG`, `INFO`, `WARNING`     |

---

## Database Persistence Strategy

GitHub Actions runners are ephemeral — the filesystem is wiped after every job.
This project uses **two complementary strategies** to persist the SQLite database:

1. **`actions/cache`** — caches `database/configs.db` between runs using a fixed
   cache key. This is the primary mechanism: each run restores the cache at the
   start and saves it at the end.

2. **`actions/upload-artifact`** — uploads the DB as a named artifact after each
   run (retained for 7 days). Useful as a backup and for debugging.

> **Note:** GitHub's cache has a 10 GB per-repo limit. The SQLite DB only grows
> by a few KB per run, so this is not a concern in practice.

---

## Message Format

Each Telegram message looks like:

```
📡 کانفیگ‌های جدید یافت شد

vmess://eyJhZGRyZXNzIjoiZXhhbXBsZS5jb20iLCAicHMiOiJvcmlnaW5hbC1uYW1lIn0=
vless://abc123@1.2.3.4:443?security=tls#original-remark
trojan://password@server.com:443#original-remark

━━━━━━━━━━━━
وی پی ان آیپی ثابت ارزان قیمت
@zirolost
```

Original remarks are never touched. The footer is appended only to the
Telegram message body.

---

## Local Development

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

export BOT_TOKEN="your_token"
export CHAT_ID="@your_channel"

python main.py
```

---

## License

MIT — free to use, modify, and redistribute.
