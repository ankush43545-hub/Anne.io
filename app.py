import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
TOKEN = "8524330304:AAF2xKJG4oJuFroFEU3f9C0R3I1UfU28h9I"
# IMPORTANT: Ensure this URL exactly matches your Render service URL
RENDER_URL = "https://anne-io.onrender.com" 
bot = telebot.TeleBot(TOKEN)

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
    except Exception as e:
        print(f"Lore Load Error: {e}")
        return "You are Anne, a chill girl from Delhi."

SYSTEM_PROMPT = get_lore()
tg_history = {}

def ask_anne(user_message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Safety check for history format
    for h in history:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
            
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat_completion(messages, max_tokens=100, temperature=0.7)
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI Error: {e}")
        return "my brain is lagging.. wait a sec"

# --- TELEGRAM WEBHOOK LOGIC ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403

@app.route("/")
def webhook_setup():
    bot.remove_webhook()
    # Adding a small delay or check here is good practice
    success = bot.set_webhook(url=RENDER_URL + '/' + TOKEN)
    if success:
        return "Anne's Telegram Bridge is Active!", 200
    return "Webhook setup failed.. check your RENDER_URL", 500

@bot.message_handler(func=lambda message: True)
def handle_telegram(message):
    chat_id = message.chat.id
    if chat_id not in tg_history:
        tg_history[chat_id] = []
    
    reply = ask_anne(message.text, tg_history[chat_id])
    
    tg_history[chat_id].append({"role": "user", "content": message.text})
    tg_history[chat_id].append({"role": "assistant", "content": reply})
    tg_history[chat_id] = tg_history[chat_id][-10:]
    
    bot.send_message(chat_id, reply)

# --- WEB UI LOGIC ---
@app.route("/chat", methods=["POST"])
def web_chat():
    data = request.json
    user_msg = data.get("message")
    history = data.get("history", [])
    reply = ask_anne(user_msg, history)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
