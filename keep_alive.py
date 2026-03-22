from flask import Flask, jsonify
import threading
import time
import requests
import os

app = Flask(__name__)

@app.route("/")
def index():
    return "♂️ Gachi-Bot is alive, Aniki! ♂️"

@app.route("/health")
def health():
    return jsonify({"status": "ok", "bot": "Billy Herrington ♂️"}), 200

@app.route("/ping")
def ping():
    return "pong", 200

def _ping_loop():
    """Пінгує себе кожні 4 хвилини щоб Render не засинав"""
    time.sleep(30)

    url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not url:
        print("⚠️ RENDER_EXTERNAL_URL не встановлено — self-ping вимкнено")
        return

    ping_url = f"{url}/ping"
    print(f"🔄 Self-ping запущено: {ping_url}")

    # Заголовки щоб обійти Cloudflare
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GachiBot/1.0)",
        "Accept": "text/plain",
        "Cache-Control": "no-cache",
    }

    while True:
        try:
            r = requests.get(ping_url, headers=headers, timeout=15)
            if r.status_code == 200:
                print(f"✅ Self-ping OK")
            else:
                print(f"⚠️ Self-ping: {r.status_code}")
        except Exception as e:
            print(f"❌ Self-ping помилка: {e}")
        time.sleep(240)  # 4 хвилини

def keep_alive():
    threading.Thread(target=_ping_loop, daemon=True).start()
    port = int(os.getenv("PORT", 8080))
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False),
        daemon=True,
    ).start()
