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
    return jsonify({"pong": True}), 200

def _ping_loop():
    """Пінгує себе кожні 4 хвилини щоб Render не засинав"""
    # Чекаємо поки сервер стартує
    time.sleep(30)
    
    url = os.getenv("RENDER_EXTERNAL_URL", "")
    if not url:
        # Спробуємо знайти URL автоматично
        print("⚠️ RENDER_EXTERNAL_URL не встановлено — self-ping вимкнено")
        return
    
    ping_url = f"{url}/ping"
    print(f"🔄 Self-ping запущено: {ping_url}")
    
    while True:
        try:
            r = requests.get(ping_url, timeout=10)
            print(f"✅ Self-ping: {r.status_code}")
        except Exception as e:
            print(f"❌ Self-ping помилка: {e}")
        time.sleep(240)  # 4 хвилини (Render засинає після 15 хв)

def keep_alive():
    # Запускаємо ping loop у фоні
    threading.Thread(target=_ping_loop, daemon=True).start()
    
    # Запускаємо Flask
    port = int(os.getenv("PORT", 8080))
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False),
        daemon=True,
    ).start()
