import os
import threading
from flask import Flask
import telebot
import google.generativeai as genai

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active!"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="You are an English tutor. Correct grammar mistakes under '💡 Correction:' and reply in simple English with a follow-up question."
)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Hello! Send me a text or voice message to practice your English.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        response = model.generate_content([
            "Listen and reply in simple English:",
            {"mime_type": "audio/ogg", "data": downloaded_file}
        ])
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Voice Error: {str(e)}")

def start_polling():
    bot.infinity_polling(skip_pending_webhooks=True)

# تشغيل البوت في مسار منفصل عند بدء تطبيق Flask
threading.Thread(target=start_polling, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
