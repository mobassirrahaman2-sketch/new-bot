import telebot
import random
import json
import os
import time
from datetime import datetime
from telebot import types

# --- কনফিগারেশন ---
TOKEN = '8891922362:AAHO4AuDrtHm0TjFl7ZFkUyKFNXj05n5dCA'  # 👈 এখানে আপনার বটের আসল টোকেনটি বসিয়ে দিন
ADMIN_ID = 8634645150  # আপনার অ্যাডমিন চ্যাট আইডি

bot = telebot.TeleBot(TOKEN)

# --- ডাটাবেজ সেটআপ (JSON ফাইল নিরাপদ ও কারাপশন-মুক্ত রাখার ব্যবস্থা) ---
DB_FILE = 'db.json'

def load_db():
    if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # নিশ্চিত করা যে সব প্রয়োজনীয় কী (Keys) ডাটাবেজে আছে
                if "users" not in data: data["users"] = {}
                if "tasks" not in data: data["tasks"] = []
                if "task_counter" not in data: data["task_counter"] = 1
                return data
        except Exception:
            print("⚠️ ডাটাবেজ ফাইলে সমস্যা হয়েছিল, নতুন ডাটাবেজ তৈরি করা হচ্ছে...")
    return {"users": {}, "tasks": [], "task_counter": 1}

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ ডাটা সেভ করতে সমস্যা হয়েছে: {e}")

db = load_db()
user_states = {}

# --- নাম ও পাসওয়ার্ড জেনারেটর ---
FIRST_NAMES = ["Sem", "John", "Alex", "David", "Michael", "Robert", "William", "James"]
LAST_NAMES = ["Rodrigue", "Rodrigues", "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller"]

def get_dynamic_password():
    day = datetime.now().strftime("%d")
    return f"rafi@{day}"

def check_user(chat_id, referrer_id=None):
    chat_id = str(chat_id)
    if chat_id not in db["users"]:
        db["users"][chat_id] = {
            "balance": 0.0, 
            "completed_tasks": 0, 
            "pending_tasks": 0,
            "referred_by": referrer_id,
            "referral_count": 0
        }
        if referrer_id and str(referrer_id) in db["users"]:
            db["users"][str(referrer_id)]["referral_count"] += 1
        save_db(db)

def get_main_keyboard(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('📷 কাজ'), types.KeyboardButton('💰 ব্যালেন্স'))
    markup.row(types.KeyboardButton('💸 টাকা উত্তোলন'), types.KeyboardButton('🎁 My Referrals'))
    if int(chat_id) == ADMIN_ID:
        markup.row(types.KeyboardButton('👑 অ্যাডমিন প্যানেল (Admin)'))
    return markup

# --- অটো-রিভিউ ফাংশন (পরপর কাজ দেখানোর জন্য) ---
def send_next_admin_review():
    pending_task = next((t for t in db["tasks"] if t["status"] == "pending"), None)
    if not pending_task:
        try:
            bot.send_message(ADMIN_ID, "✅ আর কোনো পেন্ডিং কাজ অবশিষ্ট নেই!")
        except: pass
        return
        
    review_msg = (f"📝 *টাস্ক আইডি: {pending_task['id']}*\n👤 ইউজার আইডি: {pending_task['user_id']}\n"
                  f"🏷️ টাইপ: {pending_task['type']}\n👤 নাম: {pending_task['first_name']} {pending_task['last_name']}\n"
                  f"🔑 পাসওয়ার্ড: `{pending_task['password']}`\n🆔 UID: `{pending_task['uid']}`\n"
                  f"🍪 Cookies: `{pending_task['cookies']}`\n\nঅনুমোদন করতে নিচের বাটনে চাপুন:")
                  
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.row(
        types.InlineKeyboardButton(text='✅ Approve (4.00 ৳)', callback_data=f"app_{pending_task['id']}"), 
        types.InlineKeyboardButton(text='❌ Reject', callback_data=f"rej_{pending_task['id']}")
    )
    try:
        bot.send_message(ADMIN_ID, review_msg, parse_mode='Markdown', reply_markup=inline_kb)
    except: pass

# --- কমান্ড ও মেসেজ হ্যান্ডলার ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    if chat_id in user_states: del user_states[chat_id]
    
    text = message.text.split()
    referrer_id = None
    if len(text) > 1 and text[1].isdigit():
        possible_referrer = text[1]
        if possible_referrer != str(chat_id):
            referrer_id = possible_referrer
            
    check_user(chat_id, referrer_id)
    bot.send_message(
        chat_id, 
        "👋 কাজ শুরু করতে নিচের অপশনগুলো ব্যবহার করুন 👇", 
        reply_markup=get_main_keyboard(chat_id)
    )

@bot.message_handler(func=lambda msg: msg.text == '🔙 ব্যাক')
def go_back(message):
    chat_id = message.chat.id
    if chat_id in user_states: 
        del user_states[chat_id]
    bot.send_message(chat_id, "🔙 আপনি মূল মেনুতে ফিরে এসেছেন:", reply_markup=get_main_keyboard(chat_id))

@bot.message_handler(func=lambda msg: msg.text == '📷 কাজ')
def show_jobs(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('🌐 Facebook কাজ'), types.KeyboardButton('🔙 ব্যাক'))
    bot.send_message(message.chat.id, "সিলেক্ট করুন:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == '🌐 Facebook কাজ')
def fb_job_options(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('📱 Number'))
    markup.row(types.KeyboardButton('🔙 ব্যাক'))
    bot.send_message(message.chat.id, "সিলেক্ট করুন:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == '📱 Number')
def fb_task_start(message):
    chat_id = message.chat.id
    check_user(chat_id)
    
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    password = get_dynamic_password()
    
    user_states[chat_id] = {
        'first_name': first_name,
        'last_name': last_name,
        'password': password,
        'step': 'WAITING_UID'
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('📤 Send UID'))
    markup.row(types.KeyboardButton('❓ কিভাবে কাজ করবেন'))
    markup.row(types.KeyboardButton('🔙 ব্যাক'))
    
    msg_text = (f"First name: `{first_name}`\n"
                f"Last name: `{last_name}`\n"
                f"Password: `{password}`\n\n"
                f"💰 *প্রতিটি সফল একাউนต์ সাবমিটের জন্য পাবেন: 4 টাকা।*\n\n"
                f"⚠️ **অবশ্যই মোবাইল নম্বর দিয়ে একাউন্ট করতে হবে।**\n\n"
                f"👉 উপরের তথ্যগুলোতে ট্যাপ করে কপি করুন এবং অ্যাকাউন্ট খুলে নিচে Send UID বাটনে চাপ দিন 😁")
                
    bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: msg.text == '❓ কিভাবে কাজ করবেন')
def how_to_work(message):
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(types.InlineKeyboardButton(text="📺 ভিডিওটি দেখুন (Click Here)", url="https://t.me/ff20rafi"))
    
    back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_markup.row(types.KeyboardButton('🔙 ব্যাক'))
    
    bot.send_message(
        message.chat.id, 
        "ℹ️ *কিভাবে কাজ করবেন তার সম্পূর্ণ ভিডিও গাইড আমাদের অফিশিয়াল চ্যানেলে দেওয়া আছে।* নিচের বাটনে ক্লিক করে ভিডিওটি দেখে নিন 👇", 
        parse_mode='Markdown', 
        reply_markup=inline_kb
    )

@bot.message_handler(func=lambda msg: msg.text == '📤 Send UID')
def ask_for_uid(message):
    chat_id = message.chat.id
    check_user(chat_id)
    
    if chat_id not in user_states or user_states[chat_id].get('step') != 'WAITING_UID':
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        user_states[chat_id] = {'first_name': first_name, 'last_name': last_name, 'password': get_dynamic_password()}
        
    user_states[chat_id]['step'] = 'INPUT_UID'
    
    back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_markup.row(types.KeyboardButton('🔙 ব্যাক'))
    bot.send_message(chat_id, "📝 আপনার ফেসবুক অ্যাকাউন্টের ১৪ থেকে ১৫ সংখ্যার UID-টি দিন:", reply_markup=back_markup)

@bot.message_handler(func=lambda msg: msg.text == '💸 টাকা উত্তোলন')
def withdraw_start(message):
    chat_id = str(message.chat.id)
    check_user(chat_id)
    user_balance = db["users"][chat_id]["balance"]
    
    if user_balance < 30.0:
        bot.send_message(
            message.chat.id, 
            f"❌ *দুঃখিত! আপনার ব্যালেন্স পর্যাপ্ত নয়।*\n\n"
            f"💰 আপনার বর্তমান ব্যালেন্স: {round(user_balance, 2)} টাকা\n"
            f"⚠️ সর্বনিম্ন উইথড্র পরিমাণ: *৩০ টাকা*।"
        )
        return
        
    user_states[message.chat.id] = {'step': 'WITHDRAW_METHOD'}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('📱 বিকাশ (Bkash)'), types.KeyboardButton('📱 নগদ (Nagad)'))
    markup.row(types.KeyboardButton('🔙 ব্যাক'))
    bot.send_message(message.chat.id, "💸 আপনার পেমেন্ট নেওয়ার মাধ্যমটি সিলেক্ট করুন:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == '💰 ব্যালেন্স')
def check_balance(message):
    chat_id = str(message.chat.id)
    check_user(chat_id)
    user = db["users"][chat_id]
    bot.send_message(message.chat.id, f"💵 *আপনার অ্যাকাউন্ট ব্যালেন্স*\n\n💰 মোট ব্যালেন্স: {round(user['balance'], 2)} টাকা\n⏳ পেন্ডিং কাজ: {user['pending_tasks']}টি\n✅ অনুমোদিত কাজ: {user['completed_tasks']}টি", parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == '🎁 My Referrals')
def my_referrals(message):
    chat_id = str(message.chat.id)
    check_user(chat_id)
    try:
        bot_info = bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start={chat_id}"
    except:
        referral_link = f"https://t.me/YourBot?start={chat_id}"
        
    user_data = db["users"][chat_id]
    ref_msg = (f"🎁 *আপনার রেফারেল ড্যাশবোর্ড*\n\n🔗 রেফার লিংক: `{referral_link}`\n\n👥 মোট রেফারেল সংখ্যা: {user_data.get('referral_count', 0)} জন\n💰 রেফারেল কমিশন: *৫%*")
    bot.send_message(message.chat.id, ref_msg, parse_mode='Markdown')

# --- টেক্সট ইনপুট ও প্রসেস হ্যান্ডলিং ---
@bot.message_handler(func=lambda msg: True)
def handle_all_inputs(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    # 👑 অ্যাডমিন প্যানেল
    if text == '👑 অ্যাডমিন প্যানেল (Admin)' and chat_id == ADMIN_ID:
        pending = len([t for t in db["tasks"] if t["status"] == "pending"])
        approved = len([t for t in db["tasks"] if t["status"] == "approved"])
        
        inline_kb = types.InlineKeyboardMarkup(row_width=1)
        inline_kb.add(
            types.InlineKeyboardButton(text='🔍 পেন্ডিং কাজ যাচাই করুন (Approve/Reject)', callback_data='admin_review'),
            types.InlineKeyboardButton(text='📋 সকল কাজের তালিকা দেখুন (শুধুমাত্র পেন্ডিং)', callback_data='admin_view_all_tasks')
        )
        bot.send_message(chat_id, f"📊 *অ্যাডমিন ড্যাশবোর্ড*\n\n⏳ মোট পেন্ডিং কাজ: {pending}টি\n✅ মোট অনুমোদিত কাজ: {approved}টি", parse_mode='Markdown', reply_markup=inline_kb)
        return

    # 💰 অ্যাডমিন সিক্রেট কমান্ড
    if text.startswith('/addmoney') and chat_id == ADMIN_ID:
        try:
            parts = text.split()
            target_id = str(parts[1])
            amount_to_add = float(parts[2])
            
            if target_id in db["users"]:
                db["users"][target_id]["balance"] += amount_to_add
                save_db(db)
                bot.send_message(ADMIN_ID, f"✅ সফলভাবে ইউজার `{target_id}` এর অ্যাকাউন্টে {amount_to_add} ৳ যোগ করা হয়েছে।", parse_mode='Markdown')
                try:
                    bot.send_message(target_id, f"🎁 অ্যাডমিন আপনার অ্যাকাউন্টে {amount_to_add} ৳ যোগ করে দিয়েছে!")
                except: pass
            else:
                bot.send_message(ADMIN_ID, "❌ এই আইডিটি ডাটাবেজে পাওয়া যায়নি!")
        except Exception:
            bot.send_message(ADMIN_ID, "⚠️ ফরম্যাট: `/addmoney ইউজার_আইডি পরিমাণ`")
        return

    if chat_id not in user_states:
        bot.send_message(chat_id, "সঠিক অপশনটি নির্বাচন করুন:", reply_markup=get_main_keyboard(chat_id))
        return

    current_step = user_states[chat_id].get('step')

    if current_step == 'INPUT_UID':
        if not text.isdigit() or not (14 <= len(text) <= 15):
            bot.send_message(chat_id, "❌ দুঃখিত, এটি সঠিক UID নয়! দয়া করে ১৪ বা ১৫ ডিজিটের সঠিক UID দিন।")
            return
            
        user_states[chat_id]['uid'] = text
        user_states[chat_id]['step'] = 'INPUT_COOKIES'
        
        back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_markup.row(types.KeyboardButton('🔙 ব্যাক'))
        bot.send_message(chat_id, "🍪 এবার আপনার ফেসবুক অ্যাকাউন্টের Cookies-টি দিন:", reply_markup=back_markup)

    elif current_step == 'INPUT_COOKIES':
        if "c_user=" not in text or "xs=" not in text:
            bot.send_message(chat_id, "⚠️ আপনার দেওয়া Cookies সঠিক নয়!\nদয়া করে ব্রাউজার থেকে সম্পূর্ণ কুকিজ কপি করে পেস্ট করুন।")
            return
            
        data = user_states[chat_id]
        user_id_str = str(chat_id)
        
        task_id = db["task_counter"]
        task_data = {
            "id": task_id,
            "user_id": user_id_str,
            "type": "Facebook (Number)",
            "first_name": data.get('first_name', 'N/A'),
            "last_name": data.get('last_name', 'N/A'),
            "password": data.get('password', 'N/A'),
            "uid": data['uid'],
            "cookies": text,
            "status": "pending",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        db["tasks"].append(task_data)
        db["task_counter"] += 1
        db["users"][user_id_str]["pending_tasks"] += 1
        save_db(db)
        
        del user_states[chat_id]
        bot.send_message(chat_id, "⏳ *আপনার ফেসবুক কাজ সফলভাবে সাবমিট হয়েছে!*\nঅ্যাডমিন এটি যাচাই করে সঠিক হলে আপনার ব্যালেন্সে ৪.০০ ৳ যোগ করে দেবে।", parse_mode='Markdown', reply_markup=get_main_keyboard(chat_id))
        try:
            bot.send_message(ADMIN_ID, "🔔 *ফেসবুকের নতুন কাজ এসেছে!*\nযাচাই করতে অ্যাডমিন প্যানেল চেক করুন।")
        except: pass

    elif current_step == 'WITHDRAW_METHOD':
        if text not in ['📱 বিকাশ (Bkash)', '📱 নগদ (Nagad)']:
            bot.send_message(chat_id, "❌ দয়া করে নিচের বাটন থেকে সঠিক মেথডটি সিলেক্ট করুন।")
            return
        user_states[chat_id]['method'] = text
        user_states[chat_id]['step'] = 'WITHDRAW_AMOUNT'
        
        back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_markup.row(types.KeyboardButton('🔙 ব্যাক'))
        bot.send_message(chat_id, "💵 কত টাকা উত্তোলন করতে চান তা সংখ্যায় লিখুন (যেমন: 30, 50):\n⚠️ *মনে রাখবেন প্রতি উইথড্রতে ৫ টাকা চার্জ কেটে বাকি টাকা পাঠানো হবে।*", reply_markup=back_markup)

    elif current_step == 'WITHDRAW_AMOUNT':
        if not text.isdigit():
            bot.send_message(chat_id, "❌ দয়া করে শুধুমাত্র সংখ্যায় পরিমাণটি লিখুন (যেমন: 30):")
            return
        amount = int(text)
        if amount < 30:
            bot.send_message(chat_id, "❌ সর্বনিম্ন উইথড্র পরিমাণ হলো *৩০ টাকা*! দয়া করে ৩০ বা তার বেশি লিখুন।")
            return
            
        user_balance = db["users"][str(chat_id)]["balance"]
        if user_balance < amount:
            bot.send_message(chat_id, f"❌ আপনার অ্যাকাউন্টে পর্যাপ্ত টাকা নেই!\n💰 আপনার বর্তমান ব্যালেন্স: {round(user_balance, 2)} ৳")
            return
            
        user_states[chat_id]['amount'] = amount
        user_states[chat_id]['receive_amount'] = amount - 5
        user_states[chat_id]['step'] = 'WITHDRAW_NUMBER'
        
        back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_markup.row(types.KeyboardButton('🔙 ব্যাক'))
        bot.send_message(chat_id, "📞 আপনার কাঙ্ক্ষিত পেমেন্ট নম্বরটি (Personal Number) দিন:", reply_markup=back_markup)

    elif current_step == 'WITHDRAW_NUMBER':
        if not text.isdigit() or len(text) < 11:
            bot.send_message(chat_id, "❌ দুঃখিত, এটি সঠিক মোবাইল নম্বর নয়! দয়া করে সঠিক ১১ ডিজিটের নম্বর দিন।")
            return
            
        data = user_states[chat_id]
        user_id_str = str(chat_id)
        
        db["users"][user_id_str]["balance"] -= data['amount']
        save_db(db)
        
        success_text = (f"📥 *আপনার উইথড্র রিকোয়েস্ট সফলভাবে গ্রহণ করা হয়েছে আগামী ৪ দিনের মধ্য আপনার পাওনা টাকা আপনাকে দিয়ে দেওয়া হবে।*\n\n"
                        f"📱 মাধ্যম: {data['method']}\n"
                        f"📞 নম্বর: `{text}`\n"
                        f"💵 উইথড্র পরিমাণ: {data['amount']} ৳\n"
                        f"✂️ অ্যাডমিন চার্জ: 5 ৳\n"
                        f"💰 আপনি হাতে পাবেন: *{data['receive_amount']} ৳*\n\n"
                        f"ধন্যবাদ আমাদের সাথে থাকার জন্য! 😊")
        bot.send_message(chat_id, success_text, parse_mode='Markdown', reply_markup=get_main_keyboard(chat_id))
        
        admin_notif = (f"🔔 *নতুন উইথড্র রিকোয়েস্ট এসেছে!*\n\n"
                       f"👤 ইউজার আইডি: `{chat_id}`\n"
                       f"📱 মেথড: {data['method']}\n"
                       f"📞 নম্বর: `{text}`\n"
                       f"💵 মোট উইথড্র: {data['amount']} টাকা\n"
                       f"💰 ইউজারকে পাঠাতে হবে: *{data['receive_amount']} টাকা*")
                       
        inline_kb = types.InlineKeyboardMarkup()
        inline_kb.add(types.InlineKeyboardButton(text="✅ পেমেন্ট সম্পন্ন করুন", callback_data=f"pay_{chat_id}_{data['receive_amount']}"))
        
        try:
            bot.send_message(ADMIN_ID, admin_notif, parse_mode='Markdown', reply_markup=inline_kb)
        except: pass
        del user_states[chat_id]

# --- অ্যাডমিন ডিসিশন হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    
    if call.data == 'admin_review' and chat_id == ADMIN_ID:
        send_next_admin_review()

    elif call.data == 'admin_view_all_tasks' and chat_id == ADMIN_ID:
        pending_tasks = [t for t in db["tasks"] if t["status"] == "pending"]
        
        if not pending_tasks:
            bot.send_message(ADMIN_ID, "🎉 এই মুহূর্তে কোনো পেন্ডিং কাজ অবশিষ্ট নেই!")
            return
            
        report_text = "📋 **ইউজারদের পেন্ডিং কাজের তালিকা:**\n\n"
        for task in pending_tasks:
            report_text += (f"🔢 **টাস্ক আইডি:** #{task['id']}\n👤 **ইউজার:** `{task['user_id']}`\n"
                            f"👤 **নাম:** {task['first_name']} {task['last_name']}\n🔑 **পাসওয়ার্ড:** `{task['password']}`\n"
                            f"🆔 **UID:** `{task['uid']}`\n⚡ **অবস্থা:** {task['status']}\n-------------------------\n")
            
            if len(report_text) > 3000:
                bot.send_message(ADMIN_ID, report_text, parse_mode='Markdown')
                report_text = ""
                
        if report_text:
            bot.send_message(ADMIN_ID, report_text, parse_mode='Markdown')

    elif call.data.startswith('pay_') and chat_id == ADMIN_ID:
        try:
            _, target_user_id, paid_amount = call.data.split('_')
            success_msg = f"🎉 *আপনার টাকা সফলভাবে আপনাকে দেওয়া হয়েছে।*\n💰 পরিমাণ: *{paid_amount} ৳*"
            bot.send_message(target_user_id, success_msg, parse_mode='Markdown')
            
            bot.edit_message_text(
                chat_id=ADMIN_ID,
                message_id=call.message.message_id,
                text=call.message.text + f"\n\n✅ **[পেমেন্ট সম্পূর্ণ করা হয়েছে এবং ইউজারকে নোটিফিকেশন পাঠানো হয়েছে]**",
                reply_markup=None
            )
        except Exception:
            bot.answer_callback_query(call.id, "❌ সমস্যা হয়েছে!")

    elif (call.data.startswith('app_') or call.data.startswith('rej_')) and chat_id == ADMIN_ID:
        action, task_id = call.data.split('_')
        task_id = int(task_id)
        task = next((t for t in db["tasks"] if t["id"] == task_id), None)
        if not task or task["status"] != "pending": return
            
        target_user = str(task["user_id"])
        
        if action == "app":
            task["status"] = "approved"
            db["users"][target_user]["balance"] += 4.00
            db["users"][target_user]["completed_tasks"] += 1
            db["users"][target_user]["pending_tasks"] = max(0, db["users"][target_user]["pending_tasks"] - 1)
            
            referrer = db["users"][target_user].get("referred_by")
            if referrer and str(referrer) in db["users"]:
                db["users"][str(referrer)]["balance"] += (4.00 * 0.05)
            save_db(db)
            bot.send_message(ADMIN_ID, f"✅ টাস্ক {task_id} সফলভাবে অ্যাপ্রুভ করা হয়েছে।")
            try: bot.send_message(target_user, f"🎉 অভিনন্দন! আপনার জমা দেওয়া ফেসবুক অ্যাকাউন্টটি সঠিক পাওয়া গেছে। আপনার অ্যাকাউন্টে ৪.০০ টাকা যোগ করা হয়েছে।")
            except: pass
            
        elif action == "rej":
            task["status"] = "rejected"
            db["users"][target_user]["pending_tasks"] = max(0, db["users"][target_user]["pending_tasks"] - 1)
            save_db(db)
            bot.send_message(ADMIN_ID, f"❌ টাস্ক {task_id} রিজেক্ট করা হয়েছে।")
            try: bot.send_message(target_user, f"❌ দুঃখিত! আপনার জমা দেওয়া ফেসবুক অ্যাকাউন্টের তথ্য ভুল ছিল। তাই এটি রিজেক্ট করা হয়েছে।")
            except: pass
        
        send_next_admin_review()

# --- অনলাইন হোস্টিং ও ক্র্যাশ প্রোটেকশন লুপ ---
if __name__ == '__main__':
    print("🤖 বট ব্যাকগ্রাউন্ডে সফলভাবে রান হয়েছে...")
    while True:
        try:
            # timeout এবং long_polling_timeout সেট করায় রেন্ডার বা টারমাক্সে নেট ড্রপ করলেও কোড ক্র্যাশ করবে না
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ নেটওয়ার্ক ইরর সনাক্ত করা হয়েছে: {e}. ৫ সেকেন্ড পর রিস্টার্ট হচ্ছে...")
            time.sleep(5)
