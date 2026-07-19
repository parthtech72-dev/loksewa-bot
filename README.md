# 🔔 Loksewa Alert Bot

A free Telegram bot that automatically notifies subscribers when the **Public Service Commission of Nepal (PSC)** publishes new vacancy notices, exam schedules, or results — so job seekers never have to manually refresh [psc.gov.np](https://psc.gov.np) again.

> ⚠️ **Disclaimer:** This is an independent, unofficial project. It is not affiliated with, endorsed by, or connected to the Public Service Commission of Nepal in any way. Always verify information on the [official PSC website](https://psc.gov.np).

---

## 📖 Overview

Every year, hundreds of thousands of Nepali job seekers manually check the PSC website for new vacancy notices, exam center announcements, and results. There's no reliable, free notification system for this — so this bot fills that gap.

Users subscribe once via Telegram and automatically receive a message the moment a new notice is published, along with a direct link to the official source.

---

## ✨ Features

- **Automatic monitoring** — checks psc.gov.np every 30 minutes, no manual action needed
- **Instant Telegram alerts** — new notices are pushed directly to subscribers' chats
- **Zero missed notices** — every new notice is sent to every subscriber (no unreliable keyword filtering)
- **Self-monitoring** — the bot tracks its own health and alerts the maintainer if the target website's structure changes or an error occurs
- **Simple commands** — `/start` to subscribe, `/stop` to unsubscribe, `/status` to check bot health
- **100% free to run** — built entirely on free-tier infrastructure

---

## 🏗️ How It Works

```
┌─────────────────┐     every 30 min      ┌──────────────────┐
│  GitHub Actions  │ ─────────────────────▶│   psc.gov.np      │
│  (scheduled job) │                        │  (via Playwright) │
└────────┬─────────┘                        └───────────────────┘
         │
         │ new notice detected
         ▼
┌──────────────────┐        stores        ┌──────────────────┐
│  Supabase (DB)    │ ◀───────────────────▶│  Telegram Bot API │
│  - subscribers     │                       │  (sends alerts)   │
│  - seen_notices     │                       └──────────────────┘
│  - bot_status        │
└──────────────────┘
         ▲
         │ subscribe / unsubscribe
         │
┌──────────────────┐
│  Flask Webhook     │◀── /start /stop /status commands
│  (PythonAnywhere)   │
└──────────────────┘
```

The system has two independent parts:

1. **Scraper** (`check_notices.py`) — runs on a schedule via GitHub Actions. Uses [Playwright](https://playwright.dev) to render the JavaScript-based PSC website, extracts notices, compares them against previously seen notices in the database, and broadcasts new ones to all subscribers.
2. **Webhook** (`webhook_app.py`) — a lightweight Flask app hosted on PythonAnywhere that handles user commands (`/start`, `/stop`, `/status`) in real time via Telegram's webhook system.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Scraping | Python, Playwright |
| Bot backend | Python, Flask |
| Database | Supabase (PostgreSQL) |
| Scheduling | GitHub Actions (cron) |
| Messaging | Telegram Bot API |
| Hosting | PythonAnywhere (free tier) |

---

## 🚀 Getting Started

<details>
<summary>Click to expand setup instructions</summary>

### Prerequisites
- A [Telegram Bot Token](https://core.telegram.org/bots#botfather) from BotFather
- A free [Supabase](https://supabase.com) project
- A free [PythonAnywhere](https://www.pythonanywhere.com) account

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/loksewa-bot.git
cd loksewa-bot
```

### 2. Set up the database
Run the SQL in `migration_add_status_table.sql` (and the initial schema) in your Supabase SQL Editor to create the required tables: `subscribers`, `seen_notices`, `bot_status`.

### 3. Configure environment variables
The following secrets are required:

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase `service_role` key |
| `TELEGRAM_BOT_TOKEN` | Your bot's token from BotFather |
| `ADMIN_CHAT_ID` | Your personal Telegram chat ID (for admin alerts) |

- For the scraper: add these as **GitHub repository secrets** (Settings → Secrets and variables → Actions)
- For the webhook: set these as environment variables in your PythonAnywhere WSGI config

### 4. Deploy
- **Scraper**: Runs automatically via the included GitHub Actions workflow (`.github/workflows/scraper.yml`)
- **Webhook**: Deploy `webhook_app.py` as a Flask app on PythonAnywhere, then register the webhook:
  ```
  https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-username>.pythonanywhere.com/webhook
  ```

</details>

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/start` | Subscribe to notice alerts |
| `/stop` | Unsubscribe from alerts |
| `/status` | Check when the bot last checked for notices |

---

## 🗺️ Roadmap

- [ ] Support additional government job portals (Nepal Bank Jobs, Nepal Army/Police)
- [ ] WhatsApp support
- [ ] Smarter category-based filtering
- [ ] Public uptime dashboard

---

## 🤝 Contributing

Issues and pull requests are welcome. If you find a bug (e.g. the scraper breaking due to a website redesign), please open an issue with details.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

Built to help Nepali job seekers stay informed without the daily hassle of manually checking government websites.
