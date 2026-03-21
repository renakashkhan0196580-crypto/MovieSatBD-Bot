import telebot
import requests
import json
import os

# সার্ভার থেকে তথ্য পড়ার জন্য Environment Variables ব্যবহার
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "SkyNet Digital AI সক্রিয়! মুভি আইডি পাঠান।")

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
            # Firebase URL-এর শেষে স্লাশ থাকলে সেটি ঠিক করে মুভিজ ডেটাবেজে পাঠানো
            clean_url = FIREBASE_URL.rstrip('/')
            requests.post(f"{clean_url}/movies.json", data=json.dumps(movie_info))
            bot.reply_to(message, f"✅ {data['title']} সেভ হয়েছে!")
        else:
            bot.reply_to(message, "❌ মুভি আইডিটি সঠিক নয়।")
    except Exception as e:
        bot.reply_to(message, f"❌ সমস্যা হয়েছে: {str(e)}")

bot.polling()

