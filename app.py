import os
from flask import Flask, request, jsonify
from flask_cors import CORS  # Added for frontend connection
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)  # This allows your index.html to access the API

# Load the lore from the text file
try:
    with open("system_prompt.txt", "r") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    SYSTEM_PROMPT = "You are Anne. A Gen Z girl from Delhi."

# Initialize Hugging Face Client
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")
    history = data.get("history", [])

    # Prepare messages for the model
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Process history into the correct format for the model
    for msg in history:
        messages.append(msg)
    
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat_completion(
            messages,
            max_tokens=150,
            temperature=0.7,
        )
        anne_reply = response.choices[0].message.content
        return jsonify({"reply": anne_reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Entry point for Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
