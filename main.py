import telebot
import requests
import os
from flask import Flask
from threading import Thread
from telebot import types

app = Flask(__name__)

@app.route('/')
def home():
    return "SkyNet Digital AI: MovieSatBD Manager is Live!"

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL", "").rstrip('/')
FIREBASE_SECRET = os.getenv("FIREBASE_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# --- Utility: Firebase থেকে আইডি দিয়ে কি (Key) খোঁজা ---
def find_firebase_key(movie_id):
    res = requests.get(f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}").json()
    if res:
        for key, value in res.items():
            if str(value.get('id')) == str(movie_id):
                return key, value
    return None, None

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "আকাশ, মুভি ম্যানেজ করতে আইডি পাঠান।\nডিলিট করতে 'delete' লিখুন।\nএডিট শুরু করতে 'video' লিখুন।")

# --- প্রধান মেসেজ হ্যান্ডলার ---
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
def handle_commands(message):
    text = message.text.strip().lower()

    # ১. ডিলিট মোড চালু
    if text == "delete":
        user_data[message.chat.id] = {'action': 'delete_mode'}
        bot.reply_to(message, "🗑️ আপনি ডিলিট মোডে আছেন। যে মুভিটি মুছতে চান তার **ID** পাঠান:")
        return

    # ২. ভিডিও বা আইডি ইনপুট
    if text == "video":
        bot.reply_to(message, "📝 মুভির আইডি (TMDB ID) পাঠান:")
        return

    if text.isdigit():
        content_id = text
        
        # চেক করা হচ্ছে ইউজার কি ডিলিট মোডে আছে কিনা
        if user_data.get(message.chat.id, {}).get('action') == 'delete_mode':
            perform_delete(message, content_id)
        else:
            handle_save_or_edit(message, content_id)

# --- ডিলিট করার ফাংশন ---
def perform_delete(message, content_id):
    bot.send_message(message.chat.id, f"🔍 আইডি {content_id} ডিলিট করার জন্য খোঁজা হচ্ছে...")
    fb_key, data = find_firebase_key(content_id)
    
    if fb_key:
        title = data.get('title', 'Unknown')
        del_res = requests.delete(f"{FIREBASE_URL}/movies/{fb_key}.json?auth={FIREBASE_SECRET}")
        if del_res.status_code == 200:
            bot.reply_to(message, f"✅ সফলভাবে মুছে ফেলা হয়েছে:\n*{title}*", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ ডিলিট করতে সমস্যা হয়েছে।")
    else:
        bot.reply_to(message, "⚠️ এই আইডির কোনো মুভি ডাটাবেজে নেই।")
    
    # ডিলিট শেষে মোড ক্লিয়ার করা
    if message.chat.id in user_data:
        del user_data[message.chat.id]

# --- সেভ বা এডিট করার ফাংশন ---
def handle_save_or_edit(message, content_id):
    fb_key, existing_data = find_firebase_key(content_id)
    user_data[message.chat.id] = {'id': content_id, 'fb_key': fb_key}
    
    if fb_key:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 লিঙ্ক আপডেট", callback_data="edit_link"),
                   types.InlineKeyboardButton("👁️ ভিউ পরিবর্তন", callback_data="edit_views"))
        bot.send_message(message.chat.id, f"🎬 *{existing_data.get('title')}* অলরেডি আছে। কী করতে চান?", parse_mode="Markdown", reply_markup=markup)
    else:
        # নতুন মুভি সেভ করার প্রসেস (আগের কোড অনুযায়ী)
        start_new_save_process(message, content_id)

# (বাকি ফাংশনগুলো যেমন get_link, get_views, start_new_save_process আগের মতই থাকবে)
# ... [এখানে আগের কোডের বাকি অংশটুকু থাকবে] ...

def start_new_save_process(message, content_id):
    # TMDB থেকে ডাটা নিয়ে আসার লজিক...
    url = f"https://api.themoviedb.org/3/movie/{content_id}?api_key={TMDB_API_KEY}"
    data = requests.get(url).json()
    if 'title' not in data:
        url = f"https://api.themoviedb.org/3/tv/{content_id}?api_key={TMDB_API_KEY}"
        data = requests.get(url).json()
    
    if 'title' in data or 'name' in data:
        title = data.get('title') or data.get('name')
        user_data[message.chat.id].update({'title': title, 'poster': f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}"})
        bot.send_message(message.chat.id, f"✅ নতুন মুভি: *{title}*\nলিঙ্ক দিন (বা 'skip' লিখুন):", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_link)

def get_link(message):
    link = message.text.strip()
    user_data[message.chat.id]['download_url'] = "" if link.lower() == 'skip' else link
    if user_data[message.chat.id].get('fb_key'):
        requests.patch(f"{FIREBASE_URL}/movies/{user_data[message.chat.id]['fb_key']}.json?auth={FIREBASE_SECRET}", json={'download_url': user_data[message.chat.id]['download_url']})
        bot.reply_to(message, "✅ লিঙ্ক আপডেট হয়েছে!")
    else:
        bot.reply_to(message, "👁️ কত ভিউ দেখাতে চান?")
        bot.register_next_step_handler(message, get_views)

def get_views(message):
    views = message.text.strip()
    if not views.isdigit(): return
    if user_data[message.chat.id].get('fb_key'):
        requests.patch(f"{FIREBASE_URL}/movies/{user_data[message.chat.id]['fb_key']}.json?auth={FIREBASE_SECRET}", json={'views': int(views)})
        bot.reply_to(message, "✅ ভিউ আপডেট হয়েছে!")
    else:
        user_data[message.chat.id]['views'] = int(views)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Bangla", callback_data="set_Bangla"), types.InlineKeyboardButton("Hindi", callback_data="set_Hindi"))
        bot.send_message(message.chat.id, "🌐 ভাষা:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def finalize(call):
    lang = call.data.split('_')[1]
    info = user_data[call.message.chat.id]
    final_data = {"id": info['id'], "title": info['title'], "poster": info['poster'], "download_url": info['download_url'], "views": info['views'], "language": lang}
    requests.post(f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}", json=final_data)
    bot.edit_message_text("✅ সফলভাবে সেভ হয়েছে!", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=8000)).start()
    bot.infinity_polling()
    
