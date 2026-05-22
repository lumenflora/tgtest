"""
web_server.py — Flask server
Serves the Mini App HTML and provides a REST API the Mini App calls.
Run alongside bot.py via run.py.
"""

import asyncio
import json
import threading

from flask import Flask, jsonify, request, send_from_directory

import database as db
from config import FLASK_PORT

app = Flask(__name__, static_folder="miniapp")

# We need a dedicated event loop for async DB calls from sync Flask routes
_loop = asyncio.new_event_loop()
_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_thread.start()


def run_async(coro):
    """Helper: run an async function from sync Flask context."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=10)


# ── Serve Mini App ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("miniapp", "index.html")


# ── Examples API ──────────────────────────────────────────────────────────────

@app.route("/api/examples", methods=["GET"])
def get_examples():
    examples = run_async(db.get_examples(limit=20))
    return jsonify(examples)


@app.route("/api/examples", methods=["POST"])
def add_example():
    data    = request.get_json()
    text    = data.get("text", "").strip()
    img_url = data.get("image_url")
    if not text:
        return jsonify({"error": "text is required"}), 400
    ex_id = run_async(db.add_example(text, img_url))
    return jsonify({"id": ex_id, "text": text})


@app.route("/api/examples/<int:ex_id>", methods=["DELETE"])
def delete_example(ex_id):
    run_async(db.delete_example(ex_id))
    return jsonify({"deleted": ex_id})


# ── Pending posts API ─────────────────────────────────────────────────────────

@app.route("/api/pending", methods=["GET"])
def get_pending():
    posts = run_async(db.get_all_pending())
    return jsonify(posts)


def run_flask():
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False, use_reloader=False)
