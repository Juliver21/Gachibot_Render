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
    return jsonify({"status": "ok", "bot": "Billy Bot ♂️"}), 200

def _ping_loop():
    """Пінгує себе кожні 10 хвилин щоб Render не засинав"""
    # Чекаємо поки сервер стартує
    time.sleep(30)
    url = os.getenv("RENDER_EXTERNAL_URL", "")
    if not url:
        print("⚠️ RENDER_EXTERNAL_URL не встановлено — self-ping вимкнено")
        return
    while True:
        try:
            r = requests.get(f"{url}/health", timeout=10)
            print(f"🔄 Self-ping: {r.status_code}")
        except Exception as e:
            print(f"❌ Ping failed: {e}")
        time.sleep(600)  # кожні 10 хвилин

def keep_alive():
    # Запускаємо Flask
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    # Запускаємо self-ping
    ping_thread = threading.Thread(target=_ping_loop, daemon=True)
    ping_thread.start()
