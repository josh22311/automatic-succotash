import os
from threading import Thread
from flask import Flask
from bot.bot import main as run_bot

app = Flask(__name__)
_bot_thread = None

@app.before_first_request
def _start_bot():
  global _bot_thread
  if _bot_thread is None:
    _bot_thread = Thread(target=run_bot, daemon=True)
    _bot_thread.start()

@app.get("/health")
def health():
  return "ok", 200

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))