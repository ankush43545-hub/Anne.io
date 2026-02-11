import os
import sqlite3
from hashlib import sha1
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
# SQLite Memory Setup (Fresh Brain)
# -----------------------------
conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# -----------------------------
# Generate Safe Unique User ID (No Frontend Change Needed)
# -----------------------------
def get_user_id(data, req):
    uid = data.get("user_id")
    if uid:
        return uid
    # fallback unique id from device/network
    key = (req.remote_addr or "") + (req.headers.get("User-Agent",""))
    return "anon_" + sha1(key.encode()).hexdigest()[:12]

# -----------------------------
# Save Memory
# -----------------------------
def save_memory(user_id, role, message):
    cursor.execute(
        "INSERT INTO memories (user_id, role, message) VALUES (?, ?, ?)",
        (user_id, role, message)
    )
    conn.commit()

# -----------------------------
# Load Memory (Recent Only)
# -----------------------------
def load_memory(user_id, limit=8):
    cursor.execute(
        "SELECT role, message FROM memories WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    rows.reverse()
    return "\n".join([f"{r[0]}: {r[1]}" for r in rows])

# -----------------------------
# Load System Prompt
# -----------------------------
def get_lore():
    if os.path.exists("system_prompt.txt"):
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "You are Anne, a friendly assistant who remembers past conversations."

# -----------------------------
# Chat API (Frontend-Compatible)
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        user_id = get_user_id(data, request)

        lore = get_lore()
        memory = load_memory(user_id)

        # Save user message
        if user_message:
            save_memory(user_id, "user", user_message)

        # Build prompt with memory
        prompt = f"""
{lore}

PAST MEMORY:
{memory if memory else "(no previous memory)"}

USER SAYS:
{user_message}

REPLY AS AN INTELLIGENT ASSISTANT THAT REMEMBERS THE USER.
"""

        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )

        reply = response.choices[0].message.content.strip()

        # Save bot reply
        save_memory(user_id, "assistant", reply)

        # Keep frontend JSON format EXACT
        return jsonify({"response": reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "Anne is thinking... try again 💭"}), 500


# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
