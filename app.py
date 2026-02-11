import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__)
# Allow your GitHub frontend to talk to this backend
CORS(app, resources={r"/*": {"origins": "*"}})

client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct",
    token=os.environ.get("HF_TOKEN")
)

def get_lore():
    try:
        if os.path.exists("system_prompt.txt"):
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read()
        else:
            return "You are Anne, a chill girl from Delhi. Keep it short."
    except:
        return "You are Anne, a chill girl from Delhi."

SYSTEM_PROMPT = get_lore()

# ✅ Health check route
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# ✅ Chat route
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message")
        history = data.get("history", []) # Get memory from frontend

        # 1. Start with her personality
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 2. Add conversation history (Short-term memory)
        # We take the last 10 messages so she remembers context
        if history:
            messages.extend(history[-10:])

        # 3. Add the new message
        messages.append({"role": "user", "content": user_msg})

        # 4. Generate Reply (THE UNCHAINED SETTINGS)
        response = client.chat_completion(
            messages,
            max_tokens=500,   # Increased from 120 -> 500 (No length limits)
            temperature=0.85  # Increased from 0.7 -> 0.85 (More messy/human)
        )

        reply = response.choices[0].message.content

        # Returns "reply" to match your script.js
        return jsonify({"reply": reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"reply": "mera brain lag kar rha h.. wait.."}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
