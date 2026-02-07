import os
from flask import Flask, request, jsonify
from huggingface_hub import InferenceClient

app = Flask(__name__)

# Load the lore from the text file
with open("system_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

# Initialize Hugging Face Client
# Using Llama-3.3-70B-Instruct for high-quality Gen Z Hinglish
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")
    history = data.get("history", []) # To keep the conversation flow

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add history so she remembers what you said 2 mins ago
    for msg in history:
        messages.append(msg)
    
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat_completion(
            messages,
            max_tokens=150,
            temperature=0.7, # Keeps her "human" and not repetitive
        )
        anne_reply = response.choices[0].message.content
        return jsonify({"reply": anne_reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
  
