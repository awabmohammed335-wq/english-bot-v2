import os
import threading
import time
from flask import Flask
import telebot
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active!"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-3.6-flash",
    system_instruction="You are an English tutor. Correct grammar mistakes under '💡 Correction:' and reply in simple English with a follow-up question."
)

def send_text_and_voice(message, text_response):
    bot.reply_to(message, text_response)
    
    voice_path = f"voice_{message.message_id}.mp3"
    try:
        tts = gTTS(text=text_response, lang='en', slow=False)
        tts.save(voice_path)
        
        with open(voice_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio, reply_to_message_id=message.message_id)
            
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Audio Error: {str(e)}")
    finally:
        if os.path.exists(voice_path):
            os.remove(voice_path)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Hello! Send me a text or voice message to practice your English.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        response = model.generate_content(message.text)
        send_text_and_voice(message, response.text)
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
        send_text_and_voice(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Voice Error: {str(e)}")

def start_polling():
    while True:
        try:
            # إلغاء أي Webhook قديم وتصفية أي اتصال عالق
            bot.remove_webhook()
            time.sleep(2)
            print("Starting bot polling...")
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

# تشغيل البوت في خلفية تطبيق Flask
threading.Thread(target=start_polling, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
