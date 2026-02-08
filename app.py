import os
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient
import telebot # The Telegram library

app = Flask(__name__)
CORS(app)

# --- Configuration ---
TELEGRAM_TOKEN = "8524330304:AAF2xKJG4oJuFroFEU3f9C0R3I1UfU28h9I"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Initialize Hugging Face
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)

# Load the lore
try:
    with open("system_prompt.txt", "r") as f:
        SYSTEM_PROMPT = f.read()
except:
    SYSTEM_PROMPT = "You are Anne. A Gen Z girl."

# To keep track of Telegram history specifically
tg_history = {}

# --- Logic for Anne's Brain ---
def ask_anne(user_message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat_completion(messages, max_tokens=150, temperature=0.7)
        return response.choices[0].message.content
    except Exception as e:
        return "server's acting up.. gimme a sec 💀"

# --- Telegram Bot Handlers ---
@bot.message_handler(func=lambda message: True)
def handle_tg_message(message):
    chat_id = message.chat.id
    
    # Initialize history for this specific user if not exists
    if chat_id not in tg_history:
        tg_history[chat_id] = []
    
    # Get Anne's reply
    reply = ask_anne(message.text, tg_history[chat_id])
    
    # Update local memory
    tg_history[chat_id].append({"role": "user", "content": message.text})
    tg_history[chat_id].append({"role": "assistant", "content": reply})
    
    # Keep memory short so it doesn't get slow
    if len(tg_history[chat_id]) > 10:
        tg_history[chat_id] = tg_history[chat_id][-10:]
    
    bot.send_message(chat_id, reply)

# --- Web Interface Route ---
@app.route("/chat", methods=["POST"])
def web_chat():
    data = request.json
    user_message = data.get("message")
    history = data.get("history", [])
    reply = ask_anne(user_message, history)
    return jsonify({"reply": reply})

# --- Runner ---
def run_telegram():
    print("Anne is now listening on Telegram...")
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Start Telegram in the background
    threading.Thread(target=run_telegram, daemon=True).start()
    
    # Start the Web Server
    app.run(host="0.0.0.0", port=10000)
    
