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
import requests
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------
# CONFIG - GitHub Secrets bata aauncha
# ---------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

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
    url = f"{SUPABASE_URL}/rest/v1/subscribers?select=chat_id,category"
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


def main():
    if not all([SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN]):
        print("ERROR: Environment variables missing. GitHub Secrets check garnus.")
        sys.exit(1)

    print("Checking psc.gov.np for new notices (via Playwright)...")
    notices = fetch_notices()
    print(f"Found {len(notices)} notices on page.")

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
            # category == "All" bhaye sabai lai, natra matching category lai matra
            if sub.get("category") == "All" or sub.get("category") in notice["title"]:
                send_telegram_message(sub["chat_id"], message)

        save_seen_notice(notice)

    print("Done.")


if __name__ == "__main__":
    main()
