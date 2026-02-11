import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

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
            return "You are Anne, a chill girl from Delhi."
    except:
        return "You are Anne, a chill girl from Delhi."

SYSTEM_PROMPT = get_lore()

# ✅ Health check route (Kept exactly same)
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# ✅ Chat route
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message")
        
        # 🧠 NEW: Try to get history if frontend sends it. 
        # If frontend doesn't send it, it defaults to [] so it won't crash.
        history = data.get("history", []) 

        # 1. Start with System Prompt
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 2. Add Memory (If available)
        if history:
            messages.extend(history[-10:])

        # 3. Add User Message
        messages.append({"role": "user", "content": user_msg})

        # 🔥 UPGRADE: Unchained Settings
        response = client.chat_completion(
            messages,
            max_tokens=500,    # Changed from 120 (Too short) -> 500 (Freedom)
            temperature=0.85   # Changed from 0.7 (Robot) -> 0.85 (Human/Messy)
        )

        reply = response.choices[0].message.content

        # ✅ CRITICAL: Kept key as "response" to match your frontend!
        return jsonify({"response": reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "Anne is zoning out.. try again 💭"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
