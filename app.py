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
            return "You are Anne, a chill girl from Delhi. Keep it short."
    except:
        return "You are Anne, a chill girl from Delhi."

SYSTEM_PROMPT = get_lore()

# ✅ Health check route (frontend expects this)
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# ✅ Chat route
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ]

        response = client.chat_completion(
            messages,
            max_tokens=120,
            temperature=0.7
        )

        reply = response.choices[0].message.content

        return jsonify({"response": reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "Anne is thinking... try again 💭"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
