import telebot
import requests
import json
import os
from flask import Flask # রেন্ডারের জন্য এটি দরকার

# Flask সেটআপ যেন রেন্ডার খুশি থাকে
app = Flask(__name__)

@app.route('/')
def home():
    return "MovieSatBD Bot is Running!"

# সিক্রেট ভেরিয়েবল
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "আকাশ, SkyNet Digital AI সচল আছে! মুভি আইডি পাঠান।")

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
def save_movie(message):
    movie_id = message.text
    tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=bn-BD"
    
    try:
        data = requests.get(tmdb_url).json()
        if 'title' in data:
            movie_info = {
                "title": data['title'],
                "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}",
                "overview": data.get('overview', 'বিবরণ নেই')
            }
            clean_url = FIREBASE_URL.rstrip('/')
            requests.post(f"{clean_url}/movies.json", data=json.dumps(movie_info))
            bot.reply_to(message, f"✅ {data['title']} সফলভাবে Firebase-এ সেভ হয়েছে!")
        else:
            bot.reply_to(message, "❌ মুভি পাওয়া যায়নি।")
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {str(e)}")

# বট এবং ফ্ল্যাক্স একসাথে চালানো
if __name__ == "__main__":
    from threading import Thread
    def run_bot():
        bot.polling(none_stop=True)
    
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
