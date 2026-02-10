import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__)

# This allows your GitHub Pages frontend to talk to this Render backend
CORS(app, resources={r"/*": {"origins": "*"}})

# AI Client - Uses the HF_TOKEN from your Render Env Variables
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)

# Load Anne's Personality
def get_lore():
    try:
        if os.path.exists("system_prompt.txt"):
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read()
        else:
            return "You are Anne, a chill girl from Delhi. Keep it short."
    except Exception as e:
        print(f"Error loading prompt: {e}")
        return "You are Anne, a chill girl from Delhi."

SYSTEM_PROMPT = get_lore()

@app.route("/", methods=["GET"])
def home():
    return "Anne's Brain is Online.. 🥀", 200

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message")
        history = data.get("history", [])

        # Construct messages for AI
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add the last few messages for memory
        for msg in history[-8:]:
            messages.append(msg)
            
        # Add current user message
        messages.append({"role": "user", "content": user_msg})

        # Get AI Response
        response = client.chat_completion(
            messages, 
            max_tokens=100, 
            temperature=0.7
        )
        
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"reply": "mera brain is lagging.. try again?"}), 500

if __name__ == "__main__":
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
