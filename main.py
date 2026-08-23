import os
import threading
from flask import Flask
import telebot
import google.generativeai as genai

# 1. إعداد سيرفر Flask وهمي لإرضاء Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

# 2. جلب المفاتيح من بيئة العمل
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="""
    You are an encouraging English learning tutor. 
    1. If the user makes a grammar or vocabulary mistake, gently correct it first under a '💡 Correction:' header.
    2. Respond to their message naturally in clear, simple English (2-3 sentences max).
    3. Always end with a question to keep the conversation going.
    """
)

# 3. معالجة النصوص
@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

# 4. معالجة البصمات الصوتية
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        response = model.generate_content([
            "Listen and reply in English:",
            {"mime_type": "audio/ogg", "data": downloaded_file}
        ])
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Voice Error: {str(e)}")

# 5. تشغيل البوت في خلفية السيرفر
def run_bot():
    bot.infinity_polling(skip_pending_webhooks=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
