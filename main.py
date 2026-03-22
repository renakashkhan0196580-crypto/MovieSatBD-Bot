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
FIREBASE_URL = os.getenv("FIREBASE_URL").rstrip('/')
FIREBASE_SECRET = os.getenv("FIREBASE_SECRET") # Koyeb-এ এটি সেট করেছেন তো?
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

# সাময়িকভাবে মুভি ডাটা রাখার জন্য ডিকশনারি
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "আকাশ, SkyNet Digital AI মুভি বট এখন হাই-সিকিউর! মুভি আইডি (TMDB ID) পাঠান।")

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
def handle_movie_id(message):
    movie_id = message.text.strip()
    if not movie_id.isdigit():
        bot.reply_to(message, "❌ দয়া করে শুধু মুভির ID সংখ্যাটি পাঠান।")
        return

    # ১. হাই-সিকিউরিটি চাবি ব্যবহার করে ডুপ্লিকেট চেক
    check_url = f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}"
    
    try:
        response = requests.get(check_url)
        existing_movies = response.json()
        
        if existing_movies:
            for key, movie in existing_movies.items():
                if str(movie.get('id')) == str(movie_id):
                    bot.reply_to(message, f"⚠️ আকাশ, আইডি {movie_id} আগে থেকেই ডাটাবেজে আছে!")
                    return
    except Exception as e:
        print(f"Duplicate Check Error: {e}")

    # মুভি আইডি ঠিক থাকলে ভাষা সিলেক্ট করতে বলা
    user_data[message.chat.id] = {'movie_id': movie_id}
    
    markup = types.InlineKeyboardMarkup()
    btn_bn = types.InlineKeyboardButton("বাংলা (Bangla)", callback_data="lang_bangla")
    btn_hi = types.InlineKeyboardButton("হিন্দি (Hindi)", callback_data="lang_hindi")
    btn_en = types.InlineKeyboardButton("ইংরেজি (English)", callback_data="lang_english")
    markup.add(btn_bn, btn_hi, btn_en)
    
    bot.send_message(message.chat.id, f"আইডি {movie_id} এর জন্য ভাষা সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def save_movie_callback(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "পুরানো সেশন, আবার আইডি পাঠান।")
        return

    selected_lang = call.data.split('_')[1].capitalize()
    movie_id = user_data[chat_id]['movie_id']

    tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=bn-BD"
    
    try:
        response = requests.get(tmdb_url)
        data = response.json()
        
        if 'title' in data:
            # ট্রেইলার না থাকলে খালি থাকবে, যা ওয়েবসাইটকে 'Premium/Coming Soon' দেখাতে সাহায্য করবে
            trailer_url = "" 
            
            movie_info = {
                "id": movie_id,
                "title": data['title'],
                "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}",
                "overview": data.get('overview', 'বিবরণ নেই'),
                "language": selected_lang,
                "video_url": trailer_url, 
                "download_url": "", # এটি খালি থাকলে ওয়েবসাইট বুঝবে মুভিটি এখনও আসেনি
                "status": "Coming Soon"
            }
            
            # ২. হাই-সিকিউরিটি চাবি ব্যবহার করে ডাটা সেভ করা
            firebase_post_url = f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}"
            
            res = requests.post(firebase_post_url, json=movie_info)
            if res.status_code == 200:
                bot.edit_message_text(f"✅ *{data['title']}* ({selected_lang})\nসফলভাবে সেভ হয়েছে এবং নিরাপদ!", 
                                     chat_id, call.message.message_id, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "❌ ফায়ারবেসে সেভ করতে সমস্যা হয়েছে। সিক্রেট কি চেক করুন।")
        else:
            bot.send_message(chat_id, "❌ মুভি পাওয়া যায়নি।")
    except Exception as e:
        bot.send_message(chat_id, f"❌ এরর: {str(e)}")
    
    if chat_id in user_data:
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
        
