import os
from flask import Flask, request
import telebot
from huggingface_hub import InferenceClient

app = Flask(__name__)
TOKEN = "8524330304:AAF2xKJG4oJuFroFEU3f9C0R3I1UfU28h9I"
bot = telebot.TeleBot(TOKEN)

# Replace this with your actual Render URL
RENDER_URL = "https://anne-io.onrender.com" 

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + TOKEN)
    return "Anne's Telegram Bridge is Active!", 200

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # This is where your ask_anne logic goes
    # For now, let's just test if she responds
    bot.reply_to(message, "hey.. i'm here now. stop spamming me lol")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
