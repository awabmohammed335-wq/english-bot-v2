import os
import asyncio
import threading
import time
from flask import Flask
import telebot
import google.generativeai as genai
import edge_tts

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active!"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# استخدام موديل الفلاش السريع والمعتمد رسمياً من Google
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="You are an English tutor. Correct grammar mistakes under '💡 Correction:' and reply in simple English with a follow-up question."
)

user_sessions = {}

def get_user_chat(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = model.start_chat(history=[])
    return user_sessions[chat_id]

def send_message_with_retry(chat_session, contents, retries=5, delay=5):
    for attempt in range(retries):
        try:
            return chat_session.send_message(contents)
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "503" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise e

async def generate_voice_async(text, voice_path, retries=3):
    communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
    for attempt in range(retries):
        try:
            await communicate.save(voice_path)
            return True
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                raise e

def send_text_and_voice(message, text_response):
    bot.reply_to(message, text_response)
    
    voice_path = f"voice_{message.message_id}.mp3"
    try:
        asyncio.run(generate_voice_async(text_response, voice_path))
        
        with open(voice_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio, reply_to_message_id=message.message_id)
            
    except Exception as e:
        print(f"Audio Error: {e}")
    finally:
        if os.path.exists(voice_path):
            os.remove(voice_path)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_sessions[message.chat.id] = model.start_chat(history=[])
    bot.reply_to(message, "Hello! Send me a text or voice message to practice your English. I will remember our context!")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        chat_session = get_user_chat(message.chat.id)
        response = send_message_with_retry(chat_session, message.text)
        send_text_and_voice(message, response.text)
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            bot.reply_to(message, "⏳ السيرفر مشغول حالياً بطلبات كثيرة، يرجى إعادة الإرسال بعد 20 ثانية.")
        else:
            bot.reply_to(message, "⚠️ حدث خطأ غير متوقع، يرجى المحاولة لاحقاً.")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        audio_data = {
            "mime_type": "audio/ogg",
            "data": downloaded_file
        }
        
        prompt = "Listen carefully to this audio and reply in simple English. Correct grammar mistakes under '💡 Correction:' if any."
        
        response = model.generate_content([prompt, audio_data])
        send_text_and_voice(message, response.text)
    except Exception as e:
        print(f"Voice Processing Error: {e}")
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            bot.reply_to(message, "⏳ السيرفر مشغول حالياً بطلبات كثيرة، يرجى إعادة الإرسال بعد 20 ثانية.")
        else:
            bot.reply_to(message, "⚠️ حدث خطأ في معالجة الصوت، يرجى إعادة المحاولة.")

def start_polling():
    while True:
        try:
            bot.remove_webhook()
            time.sleep(2)
            print("Starting bot polling...")
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

threading.Thread(target=start_polling, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


