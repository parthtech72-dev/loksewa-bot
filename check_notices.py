"""
Loksewa Vacancy Alert Bot - Scraper Script (Playwright version)
-------------------------------------------------------------------
psc.gov.np Vue.js le banaeko site ho - notices JavaScript le load garcha,
tesaile simple requests.get() le kaam gardaina (khali HTML shell matra aaucha).

Yo script le Playwright (headless browser) use garera page lai "real browser"
jastai kholcha, JavaScript chalna dincha, ani notices load bhaisakepachi
HTML bata data nikalcha. Yo real selectors (user le browser Inspect bata
patta lagaeko) prayog garcha:
  - Container: ul.update-section > li
  - Title: li बित्र <p class="line-clamp-2">
  - Link: li बित्र <a class="screenLink" href="...">
"""

import os
import sys
from datetime import datetime, timezone
import requests
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------
# CONFIG - GitHub Secrets bata aauncha
# ---------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")  # timro aafnै Telegram chat_id - error alert paune

NOTICE_PAGE_URL = "https://psc.gov.np/category/notice-advertisement/all"


def fetch_notices():
    """
    Playwright kholera psc.gov.np ko notice page bata real (JS-rendered)
    notices nikalne function.
    """
    notices = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page.goto(NOTICE_PAGE_URL, timeout=30000)

        # Notices JS le load garunjel parkhane (max 15 second)
        page.wait_for_selector("ul.update-section li", timeout=15000)

        items = page.query_selector_all("ul.update-section li")

        for item in items:
            title_el = item.query_selector("p.line-clamp-2")
            link_el = item.query_selector("a.screenLink")

            if not title_el:
                continue

            title = title_el.inner_text().strip()
            link = link_el.get_attribute("href") if link_el else ""
            if link and not link.startswith("http"):
                link = "https://psc.gov.np" + link

            notices.append({
                "id": link or title,  # unique identifier ko lagi link use garne
                "title": title,
                "link": link,
            })

        browser.close()

    return notices


def get_seen_notice_ids():
    """Supabase बाट pahile नै pathaisakeko notice ID haru ल्याउने."""
    url = f"{SUPABASE_URL}/rest/v1/seen_notices?select=notice_id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return {row["notice_id"] for row in resp.json()}


def save_seen_notice(notice):
    """Naya notice lai 'already sent' table maa save garne, duplicate na-hos bhanera."""
    url = f"{SUPABASE_URL}/rest/v1/seen_notices"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "notice_id": notice["id"],
        "title": notice["title"],
        "link": notice["link"],
    }
    requests.post(url, headers=headers, json=payload, timeout=15)


def get_all_subscribers():
    """Supabase बाट सबै subscribed users को Telegram chat_id ल्याउने."""
    url = f"{SUPABASE_URL}/rest/v1/subscribers?select=chat_id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_telegram_message(chat_id, text):
    """Ek user lai Telegram message pathaune."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=15)
    if not resp.ok:
        print(f"Failed to send to {chat_id}: {resp.text}")


def alert_admin(message):
    """Timi (admin) lai matra pathaune - subscriber haru lai hoina."""
    if not ADMIN_CHAT_ID:
        print("ADMIN_CHAT_ID set gareko chaina, admin alert skip garyo.")
        return
    send_telegram_message(ADMIN_CHAT_ID, f"⚙️ <b>Bot Admin Alert</b>\n\n{message}")


def get_bot_status():
    """bot_status table bata current status ल्याउने (consecutive_zero_runs count ko lagi)."""
    url = f"{SUPABASE_URL}/rest/v1/bot_status?id=eq.1&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else {"consecutive_zero_runs": 0}


def update_bot_status(notices_found, consecutive_zero_runs):
    """Har run pachi bot_status table update garne - /status command le yehi padhcha."""
    url = f"{SUPABASE_URL}/rest/v1/bot_status?id=eq.1"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "notices_found": notices_found,
        "consecutive_zero_runs": consecutive_zero_runs,
    }
    requests.patch(url, headers=headers, json=payload, timeout=15)


def main():
    if not all([SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN]):
        print("ERROR: Environment variables missing. GitHub Secrets check garnus.")
        sys.exit(1)

    try:
        print("Checking psc.gov.np for new notices (via Playwright)...")
        notices = fetch_notices()
        print(f"Found {len(notices)} notices on page.")

        # --- Zero-notice anomaly check (website structure change detect garna) ---
        status = get_bot_status()
        prev_zero_runs = status.get("consecutive_zero_runs", 0)

        if len(notices) == 0:
            new_zero_runs = prev_zero_runs + 1
            if new_zero_runs == 3:
                alert_admin(
                    "psc.gov.np bata lagataar 3 choti 0 notice bhetiyo.\n"
                    "Website ko design/structure change bhayeko ho ki bhanera "
                    "check garnus (Phase 1 selectors: ul.update-section, "
                    "p.line-clamp-2, a.screenLink)."
                )
        else:
            new_zero_runs = 0

        update_bot_status(len(notices), new_zero_runs)
        # --- end anomaly check ---

        seen_ids = get_seen_notice_ids()
        new_notices = [n for n in notices if n["id"] not in seen_ids]
        print(f"{len(new_notices)} naya notices.")

        if not new_notices:
            print("Naya notice chaina. Exiting.")
            return

        subscribers = get_all_subscribers()
        print(f"Sending to {len(subscribers)} subscribers...")

        for notice in new_notices:
            message = f"🔔 <b>Naya Loksewa Notice</b>\n\n{notice['title']}\n🔗 {notice['link']}"

            for sub in subscribers:
                # Sabai subscriber lai sabai notice pathaune - miss huna nadine
                send_telegram_message(sub["chat_id"], message)

            save_seen_notice(notice)

        print("Done.")

    except Exception as e:
        # Kunai pani unexpected error aaye, admin lai turuntai thaha huna
        error_summary = f"Scraper fail bhayo:\n<code>{type(e).__name__}: {e}</code>"
        print(error_summary)
        alert_admin(error_summary)
        raise  # GitHub Actions ma pani red ❌ dekhaunu parcha, tesaile re-raise garne


if __name__ == "__main__":
    main()
