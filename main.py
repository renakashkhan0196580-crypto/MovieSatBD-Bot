import telebot
import requests
import os
from flask import Flask
from threading import Thread
from telebot import types

app = Flask(__name__)

@app.route('/')
def home():
    return "SkyNet Digital AI: MovieSatBD Manager is Running!"

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL", "").rstrip('/')
FIREBASE_SECRET = os.getenv("FIREBASE_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def find_firebase_key(movie_id):
    try:
        res = requests.get(f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}").json()
        if res:
            for key, value in res.items():
                if str(value.get('id')) == str(movie_id):
                    return key, value
    except: pass
    return None, None

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id != ADMIN_ID: return
    user_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "আকাশ, মুভি ম্যানেজ করতে আইডি পাঠান।\nডিলিট করতে 'delete' লিখুন।\nএডিট করতে 'video' লিখুন।")

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
def handle_text(message):
    text = message.text.strip().lower()

    if text == "delete":
        user_data[message.chat.id] = {'action': 'delete_mode'}
        bot.send_message(message.chat.id, "🗑️ ডিলিট মোড: মুভির **ID** পাঠান (ব্যাকে যেতে /start লিখুন):")
        return
    if text == "video":
        bot.send_message(message.chat.id, "📝 মুভির **ID** পাঠান:")
        return

    if text.isdigit():
        if user_data.get(message.chat.id, {}).get('action') == 'delete_mode':
            perform_delete(message, text)
        else:
            handle_save_or_edit(message, text)

def handle_save_or_edit(message, content_id):
    fb_key, existing_data = find_firebase_key(content_id)
    user_data[message.chat.id] = {'id': content_id, 'fb_key': fb_key}
    
    if fb_key:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 লিঙ্ক আপডেট", callback_data=f"edit_link_{content_id}"),
                   types.InlineKeyboardButton("👁️ ভিউ পরিবর্তন", callback_data=f"edit_views_{content_id}"))
        markup.add(types.InlineKeyboardButton("🔙 ব্যাকে যান", callback_data="back_to_main"))
        bot.send_message(message.chat.id, f"🎬 *{existing_data.get('title')}* অলরেডি আছে। কী করতে চান?", parse_mode="Markdown", reply_markup=markup)
    else:
        start_new_save_process(message, content_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    
    if call.data == "back_to_main":
        bot.delete_message(chat_id, call.message.message_id)
        start(call.message)
        return

    if "edit_link" in call.data:
        msg = bot.edit_message_text("🔗 নতুন *Download/Stream Link* দিন (ব্যাকে যেতে 'back' লিখুন):", chat_id, call.message.message_id, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_link_update)
    elif "edit_views" in call.data:
        msg = bot.edit_message_text("👁️ কত ভিউ দেখাতে চান? (ব্যাকে যেতে 'back' লিখুন):", chat_id, call.message.message_id)
        bot.register_next_step_handler(msg, process_view_update)
    
    # ভাষা সেভ করার লজিক (নতুন মুভির জন্য)
    elif call.data.startswith('set_'):
        lang = call.data.split('_')[1]
        info = user_data.get(chat_id)
        if not info: return
        
        status = "Coming Soon" if not info.get('download_url') or info.get('download_url') == "" else "Watch Now"
        final_data = {
            "id": info['id'], "title": info['title'], "poster": info['poster'], "type": info.get('type','Movie'),
            "download_url": info.get('download_url', ""), "views": info.get('views', 0), "language": lang, "status": status
        }
        requests.post(f"{FIREBASE_URL}/movies.json?auth={FIREBASE_SECRET}", json=final_data)
        bot.edit_message_text(f"✅ সফলভাবে সেভ হয়েছে!\nভাষা: {lang}\nস্ট্যাটাস: {status}", chat_id, call.message.message_id)
        start(call.message)

def process_link_update(message):
    if message.text.lower() == 'back': start(message); return
    link = message.text.strip()
    fb_key = user_data[message.chat.id].get('fb_key')
    status = "Watch Now" if link != "" else "Coming Soon"
    requests.patch(f"{FIREBASE_URL}/movies/{fb_key}.json?auth={FIREBASE_SECRET}", json={'download_url': link, 'status': status})
    bot.reply_to(message, "✅ লিঙ্ক ও স্ট্যাটাস আপডেট হয়েছে!")
    start(message)

def process_view_update(message):
    if message.text.lower() == 'back': start(message); return
    if not message.text.isdigit(): return
    views = int(message.text.strip())
    fb_key = user_data[message.chat.id].get('fb_key')
    requests.patch(f"{FIREBASE_URL}/movies/{fb_key}.json?auth={FIREBASE_SECRET}", json={'views': views})
    bot.reply_to(message, f"✅ ভিউ আপডেট হয়ে {views} হয়েছে।")
    start(message)

def perform_delete(message, content_id):
    fb_key, data = find_firebase_key(content_id)
    if fb_key:
        requests.delete(f"{FIREBASE_URL}/movies/{fb_key}.json?auth={FIREBASE_SECRET}")
        bot.reply_to(message, f"✅ মুছে ফেলা হয়েছে: *{data.get('title')}*", parse_mode="Markdown")
    else: bot.reply_to(message, "⚠️ মুভিটি পাওয়া যায়নি।")
    start(message)

def start_new_save_process(message, content_id):
    url = f"https://api.themoviedb.org/3/movie/{content_id}?api_key={TMDB_API_KEY}"
    data = requests.get(url).json()
    is_tv = False
    if 'title' not in data:
        is_tv = True
        url = f"https://api.themoviedb.org/3/tv/{content_id}?api_key={TMDB_API_KEY}"
        data = requests.get(url).json()
    
    if 'title' in data or 'name' in data:
        title = data.get('title') or data.get('name')
        user_data[message.chat.id].update({'title': title, 'type': 'TV Series' if is_tv else 'Movie', 'poster': f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}"})
        bot.send_message(message.chat.id, f"✅ নতুন: *{title}*\nলিঙ্ক দিন (না থাকলে 'skip' লিখুন):", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_link)

def get_link(message):
    user_data[message.chat.id]['download_url'] = "" if message.text.lower() == 'skip' else message.text
    bot.reply_to(message, "👁️ কত ভিউ দেখাতে চান?")
    bot.register_next_step_handler(message, get_new_views)

def get_new_views(message):
    if not message.text.isdigit(): return
    user_data[message.chat.id]['views'] = int(message.text)
    markup = types.InlineKeyboardMarkup(row_width=2)
    langs = [
        types.InlineKeyboardButton("Bangla", callback_data="set_Bangla"),
        types.InlineKeyboardButton("Hindi", callback_data="set_Hindi"),
        types.InlineKeyboardButton("Tamil", callback_data="set_Tamil"),
        types.InlineKeyboardButton("English", callback_data="set_English"),
        types.InlineKeyboardButton("Arabic", callback_data="set_Arabic"),
        types.InlineKeyboardButton("Dual Audio", callback_data="set_Dual_Audio")
    ]
    markup.add(*langs)
    bot.send_message(message.chat.id, "🌐 ভাষা সিলেক্ট করুন:", reply_markup=markup)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=8000)).start()
    bot.infinity_polling()
    
