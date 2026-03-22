import telebot
import requests
import json
import os
import time
from flask import Flask
from threading import Thread

# Flask সেটআপ (Koyeb/Render এর জন্য)
app = Flask(__name__)

@app.route('/')
def home():
    return "SkyNet Digital AI: MovieSatBD Bot is Online!"

# এনভায়রনমেন্ট ভেরিয়েবল (Koyeb থেকে আসবে)
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL")
ADMIN_ID = os.getenv("ADMIN_ID")

# ADMIN_ID চেক (নিশ্চিত করা যেন এটি ইন্টিজার হয়)
if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
else:
    ADMIN_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "আকাশ, SkyNet Digital AI সচল আছে! মুভি আইডি পাঠান।")

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
def save_movie(message):
    movie_id = message.text.strip()
    if not movie_id.isdigit():
        bot.reply_to(message, "দয়া করে শুধু মুভির ID সংখ্যাটি পাঠান (যেমন: 550)।")
        return

    tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=bn-BD"
    
    try:
        response = requests.get(tmdb_url)
        data = response.json()
        
        if 'title' in data:
            movie_info = {
                "title": data['title'],
                "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}",
                "overview": data.get('overview', 'বিবরণ নেই'),
                "id": movie_id
            }
            # ফায়ারবেস লিঙ্ক ক্লিন করা
            base_url = FIREBASE_URL.rstrip('/')
            firebase_post_url = f"{base_url}/movies.json"
            
            res = requests.post(firebase_post_url, json=movie_info)
            if res.status_code == 200:
                bot.reply_to(message, f"✅ *{data['title']}*\nসফলভাবে MovieSatBD ডাটাবেজে সেভ হয়েছে!", parse_mode="Markdown")
            else:
                bot.reply_to(message, "❌ ফায়ারবেসে সেভ করতে সমস্যা হয়েছে।")
        else:
            bot.reply_to(message, "❌ মুভি পাওয়া যায়নি। আইডি ঠিক আছে তো?")
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {str(e)}")

# বট এবং ফ্ল্যাক্স একসাথে চালানোর ফাংশন
def run_flask():
    # Koyeb সাধারণত ৮০০০ পোর্ট ব্যবহার করে, তাই আমরা এনভায়রনমেন্ট থেকে নিচ্ছি
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # ১. ফ্লাস্ক অ্যাপ আলাদা থ্রেডে চালানো
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # ২. বট পোলিং চালানো (ইনফিনিটি পোলিং যেন কানেকশন না কাটে)
    print("Bot is starting...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Error occurred: {e}. Restarting in 5 seconds...")
            time.sleep(5)
            
