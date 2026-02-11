# app.py -- Drop this entire file in place of your current app.py
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
# HuggingFace Client
# -----------------------------
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct",
    token=os.environ.get("HF_TOKEN")
)

# -----------------------------
# SQLite setup
# -----------------------------
DB_PATH = "memory.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# memories: per-session conversational memory
cursor.execute("""
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# sessions: store the ChatSession JSON your frontend posts/requests
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
    """
    Use sessionId or conversationId from frontend if present.
    Otherwise generate a fallback anon id using remote_addr + user agent.
    """
    sid = None
    if isinstance(payload, dict):
        sid = payload.get("sessionId") or payload.get("conversationId") or payload.get("session_id") or payload.get("session")
    if sid:
        return str(sid)
    # fallback: make a stable-ish anon id using remote addr + UA
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
    # oldest first
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
    # ensure createdAt/updatedAt fields exist in the object as the frontend expects ChatSession shape
    session_obj.setdefault("createdAt", created_at if created_at else now_iso())
    session_obj.setdefault("updatedAt", updated_at if updated_at else now_iso())
    return session_obj

# -----------------------------
# System prompt loader (keeps behavior from your repo)
# -----------------------------
def get_lore():
    if os.path.exists("system_prompt.txt"):
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "You are Anne, a friendly assistant who remembers past conversations."

# -----------------------------
# Health (frontend uses this)
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    # simple health check - frontend expects status to reflect availability
    return jsonify({"ok": True}), 200

# -----------------------------
# Session endpoints (frontend uses these)
# POST /session  - save session object (ChatSession)
# GET  /session/<id> - retrieve stored session
# -----------------------------
@app.route("/session", methods=["POST"])
def save_session():
    try:
        payload = request.json or {}
        # frontend sends a ChatSession object with id/messages/createdAt/updatedAt
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
# Clear memory for a session (admin/utility)
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
# Chat endpoint (frontend posts: { message, conversationId, sessionId })
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "") or ""
        session_id = get_session_identifier(data, request)

        lore = get_lore()
        memory = load_memory(session_id)

        # Save user's message to memory (only if non-empty)
        if user_message.strip():
            save_memory(session_id, "user", user_message.strip())

        # Build prompt (system + memory + user message)
        prompt = f"""
{lore}

PAST MEMORY:
{memory if memory else "(no previous memory)"}

USER SAYS:
{user_message}

REPLY AS AN INTELLIGENT ASSISTANT THAT REMEMBERS THE USER.
"""

        # Call Hugging Face chat completion (same pattern your repo used)
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )

        # Try to extract reply (mirror earlier patterns)
        # Depending on HF client version this structure may vary; this matches the usage in your repo.
        reply = ""
        try:
            reply = response.choices[0].message.content
        except Exception:
            # fallback: try top-level text field
            reply = getattr(response, "text", "") or str(response)

        reply = (reply or "").strip()

        # Save assistant reply to memory
        if reply:
            save_memory(session_id, "assistant", reply)

        # Return exactly the key your frontend expects
        return jsonify({"response": reply})

    except Exception as e:
        print("chat error:", e)
        return jsonify({"response": "Anne is thinking... try again 💭"}), 500

# -----------------------------
# Run (Render will use gunicorn typically, but this helps local dev)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
