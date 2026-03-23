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
FIREBASE_URL = os.getenv("FIREBASE_URL", "").rstrip('/')
FIREBASE_SECRET = os.getenv("FIREBASE_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

# সাময়িকভাবে মুভি/সিরিজ ডাটা রাখার জন্য ডিকশনারি
user_data = {}

# TMDB থেকে ট্রেইলার লিঙ্ক খোঁজার ফাংশন (মুভি ও টিভি উভয়ের জন্য)
def get_trailer(content_id, is_tv=False):
    type_path = "tv" if is_tv else "movie"
    video_url = f"https://api.themoviedb.org/3/{type_path}/{content_id}/videos?api_key={TMDB_API_KEY}"
    try:
        res = requests.get(video_url).json()
        for video in res.get('results', []):
            if video['site'] == 'YouTube' and video['type'] in ['Trailer', 'Teaser']:
                return f"https://www.youtube.com/embed/{video['key']}"
    except:
        pass
    return ""

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "আকাশ, SkyNet Digital AI মুভি বট এখন মুভি ও সিরিজ উভয়ই সাপোর্ট করে! আইডি পাঠান।")

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
def handle_content_id(message):
    content_id = message.text.strip()
    if not content_id.isdigit():
        bot.reply_to(message, "❌ দয়া করে শুধু আইডি সংখ্যাটি পাঠান।")
        return

    # ১. ডুপ্লিকেট চেক (সিকিউরিটি কি সহ)
    check_url = f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}"
    try:
        response = requests.get(check_url)
        existing_data = response.json()
        if existing_data:
            for key, item in existing_data.items():
                if str(item.get('id')) == str(content_id):
                    bot.reply_to(message, f"⚠️ আকাশ, আইডি {content_id} আগে থেকেই ডাটাবেজে আছে!")
                    return
    except Exception as e:
        print(f"Duplicate Check Error: {e}")

    user_data[message.chat.id] = {'content_id': content_id}
    
    markup = types.InlineKeyboardMarkup()
    btn_bn = types.InlineKeyboardButton("বাংলা (Bangla)", callback_data="lang_bangla")
    btn_hi = types.InlineKeyboardButton("হিন্দি (Hindi)", callback_data="lang_hindi")
    btn_en = types.InlineKeyboardButton("ইংরেজি (English)", callback_data="lang_english")
    markup.add(btn_bn, btn_hi, btn_en)
    
    bot.send_message(message.chat.id, f"আইডি {content_id} এর জন্য ভাষা সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def save_content_callback(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "সেশন শেষ, আবার আইডি পাঠান।")
        return

    selected_lang = call.data.split('_')[1].capitalize()
    content_id = user_data[chat_id]['content_id']
    
    # ২. প্রথমে মুভি হিসেবে চেক করা, না পেলে টিভি সিরিজ হিসেবে চেক করা
    is_tv = False
    tmdb_url = f"https://api.themoviedb.org/3/movie/{content_id}?api_key={TMDB_API_KEY}&language=bn-BD"
    response = requests.get(tmdb_url).json()
    
    if 'title' not in response:
        is_tv = True
        tmdb_url = f"https://api.themoviedb.org/3/tv/{content_id}?api_key={TMDB_API_KEY}&language=bn-BD"
        response = requests.get(tmdb_url).json()

    try:
        # মুভির জন্য 'title' এবং সিরিজের জন্য 'name' ব্যবহার করা হয়
        title = response.get('title') or response.get('name')
        
        if title:
            trailer_link = get_trailer(content_id, is_tv)
            
            movie_info = {
                "id": content_id,
                "title": title,
                "poster": f"https://image.tmdb.org/t/p/w500{response.get('poster_path', '')}",
                "overview": response.get('overview', 'বিবরণ নেই'),
                "language": selected_lang,
                "video_url": trailer_link,
                "download_url": "", 
                "status": "Premium Coming Soon",
                "type": "TV Series" if is_tv else "Movie"
            }
            
            # ৩. ফায়ারবেসে ডাটা সেভ
            firebase_post_url = f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}"
            res = requests.post(firebase_post_url, json=movie_info)
            
            if res.status_code == 200:
                bot.edit_message_text(f"✅ *{title}* ({selected_lang})\nসফলভাবে সেভ হয়েছে!", 
                                     chat_id, call.message.message_id, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "❌ ফায়ারবেসে সেভ করতে সমস্যা হয়েছে।")
        else:
            bot.send_message(chat_id, "❌ মুভি বা সিরিজ পাওয়া যায়নি। আইডি চেক করুন।")
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
    bot.infinity_polling(skip_pending=True, timeout=20)
    
