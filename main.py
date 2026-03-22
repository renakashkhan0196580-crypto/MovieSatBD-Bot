import telebot
import requests
import json
import os
import time
from flask import Flask
from threading import Thread
from telebot import types

# Flask সেটআপ
app = Flask(__name__)

@app.route('/')
def home():
    return "SkyNet Digital AI: MovieSatBD Bot is Online & Secure!"

# এনভায়রনমেন্ট ভেরিয়েবল
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

# সাময়িকভাবে মুভি ডাটা রাখার জন্য ডিকশনারি
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "আকাশ, SkyNet Digital AI মুভি বট এখন আরও স্মার্ট! মুভি আইডি (TMDB ID) পাঠান।")

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
def handle_movie_id(message):
    movie_id = message.text.strip()
    if not movie_id.isdigit():
        bot.reply_to(message, "❌ দয়া করে শুধু মুভির ID সংখ্যাটি পাঠান।")
        return

    # মুভি আইডি সেভ করে ভাষা সিলেক্ট করতে বলা
    user_data[message.chat.id] = {'movie_id': movie_id}
    
    markup = types.InlineKeyboardMarkup()
    btn_bn = types.InlineKeyboardButton("বাংলা (Bangla)", callback_data="lang_bangla")
    btn_hi = types.InlineKeyboardButton("হিন্দি (Hindi)", callback_data="lang_hindi")
    btn_en = types.InlineKeyboardButton("ইংরেজি (English)", callback_data="lang_english")
    markup.add(btn_bn, btn_hi, btn_en)
    
    bot.send_message(message.chat.id, "মুভিটির ভাষা সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def save_movie_callback(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "পুরানো সেশন, আবার আইডি পাঠান।")
        return

    selected_lang = call.data.split('_')[1].capitalize()
    movie_id = user_data[chat_id]['movie_id']

    # TMDB থেকে ডাটা আনা
    tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=bn-BD"
    
    try:
        response = requests.get(tmdb_url)
        data = response.json()
        
        if 'title' in data:
            movie_info = {
                "id": movie_id,
                "title": data['title'],
                "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}",
                "overview": data.get('overview', 'বিবরণ নেই'),
                "language": selected_lang, # এখানে আপনার সিলেক্ট করা ভাষা সেভ হবে
                "video_url": "", # শুরুতে খালি থাকবে (Coming Soon এর জন্য)
                "download_url": ""
            }
            
            base_url = FIREBASE_URL.rstrip('/')
            firebase_post_url = f"{base_url}/movies.json"
            
            res = requests.post(firebase_post_url, json=movie_info)
            if res.status_code == 200:
                bot.edit_message_text(f"✅ *{data['title']}* ({selected_lang})\nসফলভাবে সেভ হয়েছে!", 
                                     chat_id, call.message.message_id, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "❌ ফায়ারবেসে কানেক্ট হতে পারেনি। রুলস চেক করুন।")
        else:
            bot.send_message(chat_id, "❌ মুভি পাওয়া যায়নি।")
    except Exception as e:
        bot.send_message(chat_id, f"❌ এরর: {str(e)}")
    
    # ডাটা ক্লিন করা
    del user_data[chat_id]

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    print("Bot is starting...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(5)
            
