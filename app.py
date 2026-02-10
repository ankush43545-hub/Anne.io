import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__, static_folder='.')

# Configure CORS to allow requests from your frontend
CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # In production, replace with your frontend domain
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# AI Client
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)

# Load Lore/System Prompt
def get_lore():
    try:
        with open("system_prompt.txt", "r") as f:
            return f.read()
    except:
        return "You are Anne, a chill girl from Delhi. Keep replies short."

SYSTEM_PROMPT = get_lore()

# In-memory session storage (for demo - use Redis/DB in production)
sessions = {}

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Anne is online!"}), 200

@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint"""
    data = request.json
    user_msg = data.get("message")
    session_id = data.get("sessionId") or data.get("conversationId", "default")
    
    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    # Get or create session history
    if session_id not in sessions:
        sessions[session_id] = []
    
    history = sessions[session_id]
    
    # Build messages for AI
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Add last 10 messages for memory efficiency
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_msg})

    try:
        response = client.chat_completion(messages, max_tokens=150, temperature=0.7)
        reply = response.choices[0].message.content
        
        # Save to session history
        sessions[session_id].append({"role": "user", "content": user_msg})
        sessions[session_id].append({"role": "assistant", "content": reply})
        
        return jsonify({
            "response": reply,
            "message": reply,
            "sessionId": session_id
        })
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({
            "response": "my brain is lagging.. try again?",
            "message": "my brain is lagging.. try again?",
            "error": str(e)
        }), 500

@app.route("/session", methods=["POST"])
def save_session():
    """Save a session (optional - for persistence)"""
    try:
        data = request.json
        session_id = data.get("id")
        if session_id:
            sessions[session_id] = data.get("messages", [])
            return jsonify({"status": "saved", "id": session_id}), 200
        return jsonify({"error": "No session ID"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/session/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get a session (optional - for persistence)"""
    if session_id in sessions:
        return jsonify({
            "id": session_id,
            "messages": sessions[session_id]
        }), 200
    return jsonify({"error": "Session not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
