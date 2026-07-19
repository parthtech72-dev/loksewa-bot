
"""
Loksewa Bot - Telegram Webhook Handler (v2 - No category filtering)
-----------------------------------------------------------------------
Yo Flask app le Telegram bot ko messages handle garcha:
- User le /start pathaye, seedhai subscribe garne (category button chaidaina)
- Warm, trust-building welcome message pathaune

Category filtering hataeko kina bhane: PSC ko notice title haru ma post
naam consistently nahune bhayera, keyword-match le kei subscriber ko
important notice miss huna sakthyo. Sabai lai sabai notice pathauda
miss hune risk hudaina.
"""

import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

WELCOME_MESSAGE = (
    "नमस्ते! 👋\n\n"
    "म Loksewa Vacancy Alert Bot हुँ — Public Service Commission (psc.gov.np) "
    "मा नयाँ विज्ञापन, नतिजा, वा सूचना आउनासाथ म तपाईंलाई सिधै यहीं पठाउँछु।\n\n"
    "✅ अब तपाईं सफलतापूर्वक subscribe हुनुभयो। कुनै पनि थप काम गर्नुपर्दैन।\n\n"
    "🔔 <b>तपाईंले किन ढुक्क हुन सक्नुहुन्छ:</b>\n"
    "म हरेक ३० मिनेटमा PSC website check गर्छु, र नयाँ notice भेटेको बित्तिकै "
    "तुरुन्तै पठाउँछु — तपाईंले कहिल्यै बारम्बार website खोल्नु पर्दैन, र कुनै "
    "पनि महत्त्वपूर्ण vacancy/result miss हुने डर लिनु पर्दैन।\n\n"
    "⚠️ <i>यो unofficial bot हो — म PSC संग सम्बन्धित छैन। सधैं आधिकारिक पुष्टिको "
    "लागि psc.gov.np हेर्नुहोस्।</i>\n\n"
    "कमाण्ड haru: /status (bot ठिक चलिरहेको छ कि हेर्न), /stop (unsubscribe गर्न)\n\n"
    "धन्यवाद भरोसा गर्नुभएकोमा 🙏"
)

ALREADY_SUBSCRIBED_MESSAGE = (
    "तपाईं पहिले नै subscribe हुनुभएको छ ✅\n"
    "नयाँ notice आउनासाथ म तपाईंलाई यहीं जानकारी दिन्छु — केही थप गर्नु पर्दैन।"
)

STOP_MESSAGE = (
    "ठिक छ, तपाईंलाई unsubscribe गरियो 👋\n"
    "अब देखि कुनै notice आउने छैन। फेरि चाहिएमा जहिले पनि /start पठाउनुहोस्।"
)

NOT_SUBSCRIBED_MESSAGE = (
    "तपाईं अहिले subscribe हुनुभएको छैन। Subscribe गर्न /start पठाउनुहोस्।"
)


def send_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)


def is_already_subscribed(chat_id):
    url = f"{SUPABASE_URL}/rest/v1/subscribers?chat_id=eq.{chat_id}&select=chat_id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return len(resp.json()) > 0


def save_subscriber(chat_id):
    url = f"{SUPABASE_URL}/rest/v1/subscribers"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    # category column ajhai database ma "not null" cha, tesaile "All" default rakhne
    # (filtering code ma prayog hudaina, tara table column khali chodna milena)
    payload = {"chat_id": chat_id, "category": "All"}
    requests.post(url, headers=headers, json=payload, timeout=15)


def delete_subscriber(chat_id):
    """Unsubscribe garne - subscribers table bata row hataune."""
    url = f"{SUPABASE_URL}/rest/v1/subscribers?chat_id=eq.{chat_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    requests.delete(url, headers=headers, timeout=15)


def get_bot_status_text():
    """/status command ko lagi bot_status table bata data ल्याएर readable text बनाउने."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

    status_resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/bot_status?id=eq.1&select=*",
        headers=headers, timeout=15,
    )
    status_rows = status_resp.json() if status_resp.ok else []

    count_resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/subscribers?select=chat_id",
        headers=headers, timeout=15,
    )
    subscriber_count = len(count_resp.json()) if count_resp.ok else "?"

    if not status_rows:
        return "अहिलेसम्म कुनै check भएको छैन।"

    status = status_rows[0]
    last_checked = status.get("last_checked", "थाहा छैन")
    notices_found = status.get("notices_found", 0)

    return (
        f"📊 <b>Bot Status</b>\n\n"
        f"⏱️ अन्तिम पटक check भएको: {last_checked}\n"
        f"📄 त्यो पटक भेटिएको notice संख्या: {notices_found}\n"
        f"👥 कुल subscribers: {subscriber_count}\n\n"
        f"म हरेक ~३० मिनेटमा autmatically check गर्छु।"
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            if is_already_subscribed(chat_id):
                send_message(chat_id, ALREADY_SUBSCRIBED_MESSAGE)
            else:
                save_subscriber(chat_id)
                send_message(chat_id, WELCOME_MESSAGE)

        elif text == "/stop":
            if is_already_subscribed(chat_id):
                delete_subscriber(chat_id)
                send_message(chat_id, STOP_MESSAGE)
            else:
                send_message(chat_id, NOT_SUBSCRIBED_MESSAGE)

        elif text == "/status":
            send_message(chat_id, get_bot_status_text())

    return jsonify({"ok": True})


@app.route("/", methods=["GET"])
def health_check():
    return "Loksewa Bot webhook is running."


if __name__ == "__main__":
    app.run(debug=True)
