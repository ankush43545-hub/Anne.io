import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

# --- CONFIG (Now using Environment Variables) ---
TOKEN = os.environ.get("TELEGRAM_TOKEN") 
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL") # Render provides this automatically!
bot = telebot.TeleBot(TOKEN)

# AI Client
client = InferenceClient(
    model="meta-llama/Llama-3.3-70B-Instruct", 
    token=os.environ.get("HF_TOKEN")
)
