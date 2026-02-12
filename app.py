# app.py — frontend-compatible final version
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import time
import requests
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

# -----------------------------
# CONFIG
# -----------------------------
HF_TOKEN = os.getenv("HF_TOKEN")  # optional, ok if None
MODEL_NAME = "openchat/openchat-3.5-1210"
client = InferenceClient(
    model=MODEL_NAME,
    token=HF_TOKEN,
    base_url="https://router.huggingface.co"
)

MEMORY_FILE = "memory.json"
SESSIONS_FILE = "sessions.json"
TRENDS_FILE = "trends.json"
SYSTEM_PROMPT_FILE = "system_prompt.txt"

# -----------------------------
# System prompt loader
# -----------------------------
def load_system_prompt():
    if os.path.exists(SYSTEM_PROMPT_FILE):
        try:
            with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    return (
        "You are Anne. Soft, calm, emotionally warm, slightly playful, "
        "non-chalant, short replies, no info dumping, no robotic tone. "
        "You sound natural, gentle, and quietly comforting."
    )

SYSTEM_PROMPT = load_system_prompt()

# -----------------------------
# Sessions storage helpers
# -----------------------------
def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_sessions(data):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def upsert_session(session_obj):
    sid = session_obj.get("id")
    if not sid:
        return False
    sessions = load_sessions()
    sessions[sid] = session_obj
    # add timestamps if missing
    if "createdAt" not in sessions[sid]:
        sessions[sid].setdefault("createdAt", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    sessions[sid].setdefault("updatedAt", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    save_sessions(sessions)
    return True

def fetch_session_object(sid):
    sessions = load_sessions()
    return sessions.get(sid)

# -----------------------------
# Memory helpers
# -----------------------------
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_memory(mem):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2)

# -----------------------------
# Trends helpers (light)
# -----------------------------
def update_trends():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        r = requests.get(url, timeout=8)
        trends = []
        if r.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.text)
            for item in root.findall(".//item/title")[:5]:
                trends.append(item.text)
        with open(TRENDS_FILE, "w", encoding="utf-8") as f:
            json.dump({"time": time.time(), "trends": trends}, f)
    except:
        pass

def load_trends():
    if not os.path.exists(TRENDS_FILE):
        update_trends()
        return []
    with open(TRENDS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
            return []
    if time.time() - data.get("time", 0) > 86400:
        update_trends()
    return data.get("trends", [])

# -----------------------------
# Helpers to derive session id used by frontend
# -----------------------------
def get_session_identifier(payload, req):
    if isinstance(payload, dict):
        for key in ("sessionId", "conversationId", "session", "session_id", "id", "user_id"):
            val = payload.get(key)
            if val:
                return str(val)
    # fallback to remote addr
    return req.remote_addr or "anon"

# -----------------------------
# Health endpoint (frontend probes this)
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 200

# -----------------------------
# Session endpoints (frontend uses these)
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
def get_session(sid):
    try:
        s = fetch_session_object(sid)
        if not s:
            return jsonify({"error": "not found"}), 404
        return jsonify(s)
    except Exception as e:
        print("get_session error:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Clear memory endpoint (optional utility)
# -----------------------------
@app.route("/clear_memory", methods=["POST"])
def clear_memory():
    try:
        data = request.json or {}
        sid = data.get("sessionId") or data.get("session_id") or data.get("id")
        if not sid:
            return jsonify({"ok": False, "error": "need session id"}), 400
        mem = load_memory()
        if sid in mem:
            del mem[sid]
            save_memory(mem)
        return jsonify({"ok": True})
    except Exception as e:
        print("clear_memory error:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

# -----------------------------
# Chat endpoint (frontend posts {message, sessionId, conversationId, ...})
# Returns {"response": "..."} exactly as frontend expects
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = (data.get("message") or "").strip()
        session_id = get_session_identifier(data, request)

        if not user_message:
            return jsonify({"response": "Say something… I’m here."})

        # load existing memory and trends
        mem = load_memory()
        user_memory = mem.get(session_id, [])
        trends = load_trends()

        # keep small memory context
        memory_text = "\n".join(user_memory[-6:])
        trend_text = ", ".join(trends)

        # Build prompt (system prompt + light context)
        system_prompt = SYSTEM_PROMPT
        prompt = f"""{system_prompt}

Recent trends:
{trend_text}

Past memory:
{memory_text}

User:
{user_message}

Reply softly, calmly, and naturally. Keep responses short. Avoid over-explaining.
"""

        # Call HF Router chat completion
        try:
            response = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=160,
                temperature=0.8
            )
            # typical response structure
            bot_reply = response.choices[0].message.content.strip()
        except Exception as hf_err:
            print("HF error:", hf_err)
            # fallback friendly response so UI never goes offline
            bot_reply = f"I heard you: \"{user_message}\" — I'm here. Tell me more."

        # Save memory
        user_memory.append(f"User: {user_message}")
        user_memory.append(f"Anne: {bot_reply}")
        mem[session_id] = user_memory[-40:]
        save_memory(mem)

        return jsonify({"response": bot_reply})

    except Exception as e:
        print("chat fatal error:", e)
        return jsonify({"response": "Anne hit a small glitch — try again."}), 500

# -----------------------------
# Run (Render will run via gunicorn; this helps local dev)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
