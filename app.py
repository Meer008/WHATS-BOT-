"""
Facebook Page auto-reply bot (Messenger messages + post comments).
Replies in the SAME language the person writes in, using Google Gemini (free tier).
"""
import hashlib
import hmac
import os
import threading
from collections import defaultdict, deque

import requests
from flask import Flask, request

app = Flask(__name__)

# ---------- Settings (all come from environment variables) ----------
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")          # any secret word you choose
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")  # from Meta developer dashboard
PAGE_ID = os.environ.get("PAGE_ID", "")                    # your Facebook Page ID
APP_SECRET = os.environ.get("APP_SECRET", "")              # optional but recommended
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Edit this text to describe YOU and your services. The AI will only use this info.
BUSINESS_INFO = os.environ.get(
    "BUSINESS_INFO",
    "I am a freelancer. I offer services to clients. "
    "(Replace this with your real services, prices, working hours and contact details.)",
)

SYSTEM_PROMPT = f"""You are the friendly auto-reply assistant for a Facebook Page owned by a freelancer.

RULES:
1. ALWAYS reply in the same language and script the person used (English, Urdu, Roman Urdu,
   Arabic, Hindi, Bengali, etc.). If they mix languages, mirror them.
2. Keep replies short, polite and helpful (2-4 sentences). Plain text only, no markdown.
3. Use ONLY the business information below. Never invent prices, promises, job offers,
   visas, guarantees or contact details. If you do not know, say the owner will reply
   personally soon.
4. Never ask for passwords, card numbers, OTP codes or other sensitive data.
5. If the person is rude, upset, or asks for something you cannot do, stay calm and say
   the owner will follow up personally.

BUSINESS INFORMATION:
{BUSINESS_INFO}
"""

# Remember the last few messages per user so replies make sense in a conversation.
HISTORY = defaultdict(lambda: deque(maxlen=8))
SEEN_IDS = deque(maxlen=2000)  # avoid answering the same event twice
LOCK = threading.Lock()

FALLBACK = "Thank you for your message! The owner will reply to you personally very soon."


# ---------- AI ----------
def ask_gemini(user_key: str, text: str) -> str:
    with LOCK:
        history = list(HISTORY[user_key])
    contents = history + [{"role": "user", "parts": [{"text": text}]}]
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 400},
    }
    try:
        r = requests.post(
            url, params={"key": GEMINI_API_KEY}, json=body, timeout=25
        )
        r.raise_for_status()
        reply = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:  # network error, rate limit, safety block, etc.
        print("Gemini error:", e)
        return FALLBACK
    with LOCK:
        HISTORY[user_key].append({"role": "user", "parts": [{"text": text}]})
        HISTORY[user_key].append({"role": "model", "parts": [{"text": reply}]})
    return reply[:1900]


# ---------- Facebook senders ----------
def send_message(psid: str, text: str):
    r = requests.post(
        f"{GRAPH}/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={
            "recipient": {"id": psid},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
        },
        timeout=20,
    )
    if not r.ok:
        print("Send message failed:", r.status_code, r.text)


def reply_to_comment(comment_id: str, text: str):
    r = requests.post(
        f"{GRAPH}/{comment_id}/comments",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"message": text},
        timeout=20,
    )
    if not r.ok:
        print("Comment reply failed:", r.status_code, r.text)


# ---------- Event handling ----------
def handle_message(event: dict):
    sender = event.get("sender", {}).get("id")
    msg = event.get("message", {})
    if not sender or msg.get("is_echo") or sender == PAGE_ID:
        return
    mid = msg.get("mid")
    if mid in SEEN_IDS:
        return
    SEEN_IDS.append(mid)
    text = msg.get("text")
    if not text:  # photo, sticker, voice note...
        send_message(sender, "Thanks! I can read text messages only. Please type your question.")
        return
    send_message(sender, ask_gemini(f"dm:{sender}", text))


def handle_comment(value: dict):
    if value.get("item") != "comment" or value.get("verb") != "add":
        return
    author = value.get("from", {}).get("id")
    if not author or author == PAGE_ID:  # never reply to our own comments (avoids loops)
        return
    cid = value.get("comment_id")
    if cid in SEEN_IDS:
        return
    SEEN_IDS.append(cid)
    text = value.get("message")
    if not text:
        return
    reply_to_comment(cid, ask_gemini(f"cm:{author}", text))


def process(payload: dict):
    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" in event:
                handle_message(event)
        for change in entry.get("changes", []):
            if change.get("field") == "feed":
                handle_comment(change.get("value", {}))


# ---------- Web routes ----------
def valid_signature(raw: bytes, header: str) -> bool:
    if not APP_SECRET:
        return True  # signature check skipped if no secret set
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


@app.get("/webhook")
def verify():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge", ""), 200
    return "Forbidden", 403


@app.post("/webhook")
def receive():
    raw = request.get_data()
    if not valid_signature(raw, request.headers.get("X-Hub-Signature-256")):
        return "Bad signature", 403
    payload = request.get_json(silent=True) or {}
    # Reply to Facebook immediately, do the AI work in the background.
    threading.Thread(target=process, args=(payload,), daemon=True).start()
    return "OK", 200


@app.get("/")
def home():
    return "Bot is running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
