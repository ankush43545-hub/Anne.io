import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__, static_folder='.')
CORS(app)

# AI Client
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)

# Load Lore
def get_lore():
    try:
        with open("system_prompt.txt", "r") as f:
            return f.read()
    except:
        return "You are Anne, a chill girl from Delhi. Keep replies short."

SYSTEM_PROMPT = get_lore()

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message")
    history = data.get("history", [])

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Add only last 10 messages for memory efficiency
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_msg})

    try:
        response = client.chat_completion(messages, max_tokens=100, temperature=0.7)
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"reply": "my brain is lagging.. try again?"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
