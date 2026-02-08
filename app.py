import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient
import telebot

app = Flask(__name__)
CORS(app)

# --- Config ---
# Better to use Render Environment Variables for these!
TELEGRAM_TOKEN = "8524330304:AAF2xKJG4oJuFroFEU3f9C0R3I1UfU28h9I"
WEBHOOK_URL = "https://anne-io.onrender.com/telegram" # Replace with your ACTUAL Render URL
bot = telebot.TeleBot(TELEGRAM_TOKEN)

client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)

# Lore setup
try:
    with open("system_prompt.txt", "r") as f:
        SYSTEM_PROMPT = f.read()
except:
    SYSTEM_PROMPT = "You are Anne. A Gen Z girl. Be chill and human."

tg_history = {}

def ask_anne(user_message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat_completion(messages, max_tokens=150, temperature=0.7)
        return response.choices[0].message.content
    except Exception:
        return "my brain is lagging.. wait a sec"

# --- TELEGRAM WEBHOOK ROUTE ---
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return jsonify({"error": "unauthorized"}), 403

@bot.message_handler(func=lambda message: True)
def handle_tg(message):
    chat_id = message.chat.id
    if chat_id not in tg_history:
        tg_history[chat_id] = []
    
    reply = ask_anne(message.text, tg_history[chat_id])
    
    tg_history[chat_id].append({"role": "user", "content": message.text})
    tg_history[chat_id].append({"role": "assistant", "content": reply})
    tg_history[chat_id] = tg_history[chat_id][-10:]
    
    bot.send_message(chat_id, reply)

# --- WEB UI ROUTE ---
@app.route("/chat", methods=["POST"])
def web_chat():
    data = request.json
    reply = ask_anne(data.get("message"), data.get("history", []))
    return jsonify({"reply": reply})

# --- SETUP WEBHOOK ON START ---
@app.route("/")
def index():
    # This sets the webhook automatically when you visit the site
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return "Anne's server is active.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
