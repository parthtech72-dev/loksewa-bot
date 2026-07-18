"""
Loksewa Bot - Telegram Webhook Handler
-----------------------------------------
Yo Flask app le Telegram bot ko messages handle garcha:
- User le /start pathaye category button haru dekhaune
- User le category select gare Supabase maa save garne

Yo app PythonAnywhere ko free tier maa host garna milcha (24/7 free, card chaidaina).
README.md ko "PHASE 4" section herna deployment ko lagi.
"""

import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

CATEGORIES = ["Kharidar", "Nayab Subba", "Officer (Adhikrit)", "All"]


def send_message(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)


def save_subscriber(chat_id, category):
    url = f"{SUPABASE_URL}/rest/v1/subscribers"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",  # chat_id duplicate bhaye update garne
    }
    payload = {"chat_id": chat_id, "category": category}
    requests.post(url, headers=headers, json=payload, timeout=15)


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    # Case 1: User le text message pathayo (jastai /start)
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            keyboard = [[{"text": cat, "callback_data": cat}] for cat in CATEGORIES]
            send_message(
                chat_id,
                "Namaste! 👋 Loksewa Vacancy Alert Bot मा स्वागत छ।\n\n"
                "तपाईं कुन category को notice पाउन चाहनुहुन्छ छान्नुहोस्:",
                keyboard=keyboard,
            )

    # Case 2: User le button (inline keyboard) click garyo
    elif "callback_query" in update:
        callback = update["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        category = callback["data"]

        save_subscriber(chat_id, category)
        send_message(
            chat_id,
            f"✅ ठिक छ! तपाईं '{category}' category को notice पाउनुहुनेछ।\n"
            "Naya vacancy आउने बित्तिकै यहीं message आउँछ।",
        )

    return jsonify({"ok": True})


@app.route("/", methods=["GET"])
def health_check():
    return "Loksewa Bot webhook is running."


if __name__ == "__main__":
    app.run(debug=True)
