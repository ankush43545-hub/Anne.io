import os
import json
import sqlite3
from hashlib import sha1
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

# -----------------------------
# FREE HuggingFace Client (NO CREDITS)
# -----------------------------
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.2"
)

# -----------------------------
# SQLite setup
# -----------------------------
DB_PATH = "memory.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# -----------------------------
# Helpers
# -----------------------------
def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def get_session_identifier(payload, req):
    sid = None
    if isinstance(payload, dict):
        sid = payload.get("sessionId") or payload.get("conversationId") or payload.get("session_id") or payload.get("session")
    if sid:
        return str(sid)

    key = (req.remote_addr or "") + (req.headers.get("User-Agent", ""))
    return "anon_" + sha1(key.encode()).hexdigest()[:12]

def save_memory(session_id, role, message):
    cursor.execute(
        "INSERT INTO memories (session_id, role, message) VALUES (?, ?, ?)",
        (session_id, role, message)
    )
    conn.commit()

def load_memory(session_id, limit=8):
    cursor.execute(
        "SELECT role, message FROM memories WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, limit)
    )
    rows = cursor.fetchall()
    rows.reverse()
    return "\n".join([f"{r[0]}: {r[1]}" for r in rows])

def upsert_session(session_obj):
    sid = session_obj.get("id")
    if not sid:
        return False

    data = json.dumps(session_obj)
    now = now_iso()

    cursor.execute("SELECT 1 FROM sessions WHERE id=?", (sid,))
    exists = cursor.fetchone()

    if exists:
        cursor.execute("UPDATE sessions SET data=?, updated_at=? WHERE id=?", (data, now, sid))
    else:
        cursor.execute("INSERT INTO sessions (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)", (sid, data, now, now))

    conn.commit()
    return True

def get_session(sid):
    cursor.execute("SELECT data, created_at, updated_at FROM sessions WHERE id=?", (sid,))
    row = cursor.fetchone()
    if not row:
        return None

    data, created_at, updated_at = row

    try:
        session_obj = json.loads(data)
    except:
        session_obj = {"id": sid, "messages": []}

    session_obj.setdefault("createdAt", created_at if created_at else now_iso())
    session_obj.setdefault("updatedAt", updated_at if updated_at else now_iso())

    return session_obj

# -----------------------------
# System Prompt Loader
# -----------------------------
def get_lore():
    if os.path.exists("system_prompt.txt"):
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "You are Anne, a friendly assistant who remembers past conversations."

# -----------------------------
# Health Endpoint
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 200

# -----------------------------
# Session Endpoints
# -----------------------------
@app.route("/session", methods=["POST"])
def save_session():
    try:
        payload = request.json or {}
        if not isinstance(payload, dict) or not payload.get("id"):
            return jsonify({"ok": False, "error": "session must include id"}), 400

        upsert_session(payload)
        return jsonify({"ok": True})

    except Exception as e:
        print("save_session error:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/session/<sid>", methods=["GET"])
def fetch_session(sid):
    try:
        session_obj = get_session(sid)
        if not session_obj:
            return jsonify({"error": "not found"}), 404
        return jsonify(session_obj)

    except Exception as e:
        print("fetch_session error:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Clear Memory
# -----------------------------
@app.route("/clear_memory", methods=["POST"])
def clear_memory():
    try:
        data = request.json or {}
        sid = data.get("sessionId") or data.get("session_id") or data.get("id")

        if not sid:
            return jsonify({"ok": False, "error": "need sessionId"}), 400

        cursor.execute("DELETE FROM memories WHERE session_id=?", (sid,))
        conn.commit()

        return jsonify({"ok": True})

    except Exception as e:
        print("clear_memory error:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

# -----------------------------
# Chat Endpoint (Frontend Compatible)
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "") or ""
        session_id = get_session_identifier(data, request)

        lore = get_lore()
        memory = load_memory(session_id)

        if user_message.strip():
            save_memory(session_id, "user", user_message.strip())

        prompt = f"""
{lore}

PAST MEMORY:
{memory if memory else "(no previous memory)"}

USER:
{user_message}

ASSISTANT:
"""

        response = client.text_generation(
            prompt=prompt,
            max_new_tokens=350,
            temperature=0.7,
            top_p=0.9
        )

        reply = (response or "").strip()

        if reply:
            save_memory(session_id, "assistant", reply)

        return jsonify({"response": reply})

    except Exception as e:
        print("chat error:", e)
        return jsonify({"response": "Anne had a temporary brain glitch — try again 💭"}), 500

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
