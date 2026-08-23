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

# استخدام موديل gemini-3.6-flash المعتمد
model = genai.GenerativeModel(
    model_name="gemini-3.6-flash",
    system_instruction="You are an English tutor. Correct grammar mistakes under '💡 Correction:' and reply in simple English with a follow-up question."
)

def send_text_and_voice(message, text_response):
    # إرسال النص أولاً
    bot.reply_to(message, text_response)
    
    try:
        # تحويل النص إلى صوت باللغة الإنجليزية
        tts = gTTS(text=text_response, lang='en', slow=False)
        voice_path = f"response_{message.chat.id}.ogg"
        tts.save(voice_path)
        
        # إرسال الملف الصوتي كرسالة صوتية في تلغرام
        with open(voice_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio, reply_to_message_id=message.message_id)
            
        # حذف الملف الصوتي المؤقت من السيرفر بعد إرساله
        if os.path.exists(voice_path):
            os.remove(voice_path)
    except Exception as voice_err:
        print(f"TTS Error: {str(voice_err)}")

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
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(none_stop=True)

# تشغيل البوت في خلفية تطبيق Flask
threading.Thread(target=start_polling, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
