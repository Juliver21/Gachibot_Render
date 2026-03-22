from flask import Flask, jsonify
import threading
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

def keep_alive():
    # Self-ping вимкнено — використай UptimeRobot для підтримки активності
    # https://uptimerobot.com → Add Monitor → HTTP → твій URL → кожні 5 хв
    port = int(os.getenv("PORT", 8080))
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False),
        daemon=True,
    ).start()
    print(f"🌐 Flask запущено на порту {port}")
