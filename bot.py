import telebot
from telebot.types import ReplyKeyboardMarkup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import random
import string
import time
import json
import os
import re

last_product_time = {}
PRODUCT_COOLDOWN = 30  # 30 giây mới gửi link tiếp
DB_FILE = "database.json"

pending_sp_users = set()

TOKEN = "8500760879:AAFjfnNsM57yGMMqyhUMxg2jKefnzxKmgYk"
ADMIN_ID = 6500271609

bot = telebot.TeleBot(TOKEN)

PRODUCT_PRICE = 100000
COMMISSION_PERCENT = 10
WITHDRAW_FEE = 0
blocked_users = set()
users = {}
orders = []
withdraw_requests = []


# ================= USER =================
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "locked": 0,
            "purchase_history": [],
            "withdraw_history": []
        }
    return users[user_id]

def check_block(message):
    if message.from_user.id in blocked_users:
        bot.send_message(
            message.chat.id,
            "🚫 Tài khoản của bạn đã bị khóa.\nVui lòng liên hệ admin."
        )
        return True
    return False
def save_data():
    data = {
        "users": users,
        "orders": orders,
        "withdraw_requests": withdraw_requests,
        "blocked_users": list(blocked_users)
    }

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def is_valid_url(url):
    regex = r"https?://[^\s]+"
    return re.match(regex, url)
    
def load_data():
    global users, orders, withdraw_requests, blocked_users

    if not os.path.exists(DB_FILE):
        return

    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

        users = {int(k): v for k, v in data.get("users", {}).items()}
        orders = data.get("orders", [])
        withdraw_requests = data.get("withdraw_requests", [])
        blocked_users = set(data.get("blocked_users", []))


# ================= MENU =================
def main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 Mua hàng", "ℹ️ Thông tin")
    markup.row("💰 Rút tiền", "📦 Lịch sử mua hàng")
    markup.row("📤 Lịch sử rút tiền", "📞 Hỗ trợ")
    if user_id == ADMIN_ID:
        markup.row("🛠 Admin Panel")
    return markup


def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Đơn chờ duyệt")
    markup.row("💳 Yêu cầu rút tiền")
    markup.row("🔙 Quay lại")
    return markup


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    if check_block(message):
        return
    bot.send_message(
        message.chat.id,
        "🎉 CHÀO MỪNG ĐẾN VỚI BOT KIẾM HOA HỒNG\n\n"
        "Vui lòng chọn chức năng bên dưới:",
        reply_markup=main_menu(message.from_user.id)
    )


# ================= MUA HÀNG =================
@bot.message_handler(func=lambda m: m.text == "🛒 Mua hàng")
def buy(message):

    if check_block(message):
        return

    pending_sp_users.add(message.from_user.id)

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔙 Quay lại")

    bot.send_message(
        message.chat.id,
        "📌 Vui lòng gửi link sản phẩm theo cú pháp:\n\n"
        "/sp + link sản phẩm\n\n"
        "Ví dụ:\n"
        "/sp https://abc.com/sanpham",
        reply_markup=markup
    )

@bot.message_handler(commands=['sp'])
def handle_sp(message):

    if check_block(message):
        return

    user_id = message.from_user.id
    now = time.time()

    if user_id in last_product_time:
        if now - last_product_time[user_id] < PRODUCT_COOLDOWN:
            bot.reply_to(
                message,
                "⏳ Vui lòng đợi 30 giây trước khi tạo đơn mới"
            )
            return

    last_product_time[user_id] = now

    if user_id not in pending_sp_users:
        return

    try:
        link = message.text.split(" ", 1)[1]
    except:
        bot.reply_to(
            message,
            "❌ Sai cú pháp.\n\n"
            "Vui lòng nhập:\n"
            "/sp + link sản phẩm"
        )
        return

    if not is_valid_url(link):
        bot.reply_to(
            message,
            "❌ Link không hợp lệ\n\nVui lòng gửi link đúng định dạng"
        )
        return

    # Tạo mã đơn DHxxxx
    order_code = "DH" + ''.join(random.choices(string.digits, k=4))
    time_now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # Lưu đơn
    orders.append({
        "code": order_code,
        "user_id": user_id,
        "original_link": link,
        "admin_link": None,
        "percent": None,
        "status": "pending",
        "time": time_now
    })

    save_data()

    user = get_user(user_id)
    user["purchase_history"].append({
        "code": order_code,
        "link": link,
        "percent": None,
        "status": "Chờ xác nhận",
        "time": time_now
    })

    save_data()

    pending_sp_users.remove(user_id)

    # Gửi sang admin
    bot.send_message(
        ADMIN_ID,
        f"🆕 ĐƠN HÀNG MỚI\n\n"
        f"👤 User ID: {user_id}\n"
        f"📦 Mã đơn: {order_code}\n"
        f"🔗 Link gốc:\n{link}\n\n"
        f"👉 Dùng lệnh:\n"
        f"/{order_code} link_moi xx%\n\n"
        f"Ví dụ:\n"
        f"/{order_code} https://refadmin.com/sp123 10%"
    )

    
    bot.send_message(
        message.chat.id,
        f"🎉 ĐÃ GHI NHẬN ĐƠN HÀNG\n\n"
        f"📦 Mã đơn: {order_code}\n"
        f"🔗 Link sản phẩm:\n{link}\n"
        f"🕒 Thời gian: {time_now}\n\n"
        f"📌 Trạng thái: Chờ admin xử lý",
    )

# ================= THÔNG TIN =================
@bot.message_handler(func=lambda m: m.text == "ℹ️ Thông tin")
def info(message):
    if check_block(message):
        return
    user = get_user(message.from_user.id)
    withdrawable = user["balance"]

    bot.send_message(
        message.chat.id,
        f"📊 THÔNG TIN TÀI KHOẢN\n\n"
        f"💰 Số dư: {user['balance']:,}đ\n"
        f"🔒 Tiền khóa: {user['locked']:,}đ\n"
        f"💵 Tiền rút được: {withdrawable:,}đ"
    )


# ================= RÚT TIỀN =================
@bot.message_handler(func=lambda m: m.text == "💰 Rút tiền")
def request_withdraw(message):
    if check_block(message):
        return
    user = get_user(message.from_user.id)

    if user["balance"] <= 0:
        bot.send_message(message.chat.id, "❌ Không đủ tiền để rút")
        return

    bot.send_message(
        message.chat.id,
        "💳 Vui lòng nhập theo mẫu:\n\n"
        "/rut NgânHàng STK Tên"
    )


@bot.message_handler(commands=['rut'])
def process_withdraw(message):

    if check_block(message):
        return

    user_id = message.from_user.id
    user = get_user(user_id)

    if user["balance"] <= 0:
        bot.reply_to(message, "❌ Không đủ tiền")
        return

    try:
        parts = message.text.split(" ",3)
        bank = parts[1]
        stk = parts[2]
        name = parts[3]
    except:
        bot.reply_to(
            message,
            "❌ Sai cú pháp\n\n"
            "/rut NgânHàng STK Tên"
        )
        return

    amount = user["balance"]

    withdraw_code = "WD" + ''.join(random.choices(string.digits, k=4))

    withdraw_requests.append({
        "code": withdraw_code,
        "user_id": user_id,
        "amount": amount,
        "bank": bank,
        "stk": stk,
        "name": name,
        "status": "pending",
        "time": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    })

    save_data()

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Duyệt", callback_data=f"duyetwd_{withdraw_code}"),
        InlineKeyboardButton("❌ Từ chối", callback_data=f"tuchoiwd_{withdraw_code}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💳 YÊU CẦU RÚT TIỀN\n\n"
        f"📄 Mã: {withdraw_code}\n"
        f"👤 User: {user_id}\n"
        f"💰 Số tiền: {amount:,}đ\n\n"
        f"🏦 Ngân hàng: {bank}\n"
        f"🔢 STK: {stk}\n"
        f"👤 Tên: {name}",
        reply_markup=markup
    )

    bot.reply_to(
        message,
        f"✅ Đã gửi yêu cầu rút tiền\n"
        f"💰 Số tiền: {amount:,}đ\n"
        f"⏳ Chờ admin duyệt"
    )

# ================= LỊCH SỬ MUA =================
@bot.message_handler(func=lambda m: m.text == "📦 Lịch sử mua hàng")
def history_buy(message):
    if check_block(message):
        return
    user = get_user(message.from_user.id)

    if not user["purchase_history"]:
        bot.send_message(message.chat.id, "Chưa có giao dịch.")
        return

    text = ""
    for item in user["purchase_history"][-5:]:
        text += (
            f"📦 {item['code']}\n"
            f"🔗 {item['link']}\n"
        )

        if item["percent"]:
            text += f"💰 Hoa hồng: {item['percent']}\n"

        text += f"📌 Trạng thái: {item['status']}\n\n"

    bot.send_message(message.chat.id, text)

# ================= LỊCH SỬ RÚT =================
@bot.message_handler(func=lambda m: m.text == "📤 Lịch sử rút tiền")
def history_withdraw(message):

    if check_block(message):
        return

    user = get_user(message.from_user.id)

    if not user["withdraw_history"]:
        bot.send_message(message.chat.id, "📤 Chưa có giao dịch rút tiền")
        return

    text = "📤 5 LẦN RÚT GẦN NHẤT\n\n"

    for item in user["withdraw_history"][-5:]:
        text += f"🕒 {item['time']} | -{item['amount']:,}đ\n"

    bot.send_message(message.chat.id, text)

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    bot.send_message(message.chat.id, "🛠 MENU ADMIN", reply_markup=admin_menu())


# ================= XEM ĐƠN =================
@bot.message_handler(func=lambda m: m.text == "📋 Đơn chờ duyệt" and m.from_user.id == ADMIN_ID)
def view_orders(message):

    waiting = [o for o in orders if o["status"] in ["pending", "waiting_check"]]

    if not waiting:
        bot.send_message(message.chat.id, "✅ Không có đơn nào")
        return

    text = "📋 DANH SÁCH ĐƠN:\n\n"

    for o in waiting:
        status_text = "🟡 Chờ admin xử lý" if o["status"] == "pending" else "🔵 User đã mua - chờ kiểm tra"

        text += (
            f"{o['code']}\n"
            f"User: {o['user_id']}\n"
            f"Trạng thái: {status_text}\n\n"
        )

    text += "Xử lý bằng lệnh:\n/DHxxxx link_moi xx%"

    bot.send_message(message.chat.id, text)

# ================= DUYỆT =================

@bot.message_handler(func=lambda m: m.text.startswith("/DH"))
def admin_process_order(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split(" ")

    if len(parts) < 3:
        return

    order_code = parts[0][1:]
    new_link = parts[1]
    percent = parts[2]

    for order in orders:
        if order["code"] == order_code and order["status"] == "pending":

            order["admin_link"] = new_link
            order["percent"] = percent
            order["status"] = "approved"

            user_id = order["user_id"]
            user = get_user(user_id)

            # Cập nhật lịch sử user
            for item in user["purchase_history"]:
                if item["code"] == order_code:
                    item["percent"] = percent
                    item["status"] = "Đã xử lý"
                    item["link"] = new_link

            # Tạo nút inline
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Đã mua", callback_data=f"bought_{order_code}"),
                InlineKeyboardButton("🔙 Quay lại", callback_data="back_menu")
            )

            bot.send_message(
               user_id,
               f"🎉 ĐƠN HÀNG ĐÃ ĐƯỢC XỬ LÝ\n\n"
               f"📦 Mã đơn: {order_code}\n\n"
               f"🔗 Link mua hàng:\n{new_link}\n\n"
               f"💰 Hoa hồng ước tính:\n{percent}",
               reply_markup=markup
            )
# ================= HỖ TRỢ =================
@bot.message_handler(func=lambda m: m.text == "📞 Hỗ trợ")
def support(message):
    bot.send_message(
        message.chat.id,
        "📞 TRUNG TÂM HỖ TRỢ\n\n"
        "❓ Gặp vấn đề khi tạo đơn?\n"
        "❓ Hoa hồng chưa cập nhật?\n"
        "❓ Rút tiền bị chậm?\n\n"
        "👑 @tuananhdz\n"
        "⏰ 8h - 22h mỗi ngày"
    )


# ================= QUAY LẠI =================
@bot.message_handler(func=lambda m: m.text == "🔙 Quay lại")
def back(message):
    bot.send_message(
        message.chat.id,
        "🔙 Quay về menu chính",
        reply_markup=main_menu(message.from_user.id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("bought_"))
def user_confirm_bought(call):

    order_code = call.data.split("_")[1]
    user_id = call.from_user.id
    confirm_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # Cập nhật trạng thái
    for order in orders:
        if order["code"] == order_code:
            order["status"] = "waiting_check"
            order["confirmed_time"] = confirm_time
            break

    # Thông báo admin
    bot.send_message(
        ADMIN_ID,
        f"📢 USER ĐÃ NHẤN ĐÃ MUA\n\n"
        f"👤 User: {user_id}\n"
        f"📦 Mã đơn: {order_code}\n"
        f"🕒 {confirm_time}"
    )

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        f"⏳ ĐÃ GỬI XÁC NHẬN\n\n"
        f"📦 Mã đơn: {order_code}\n"
        f"📌 Trạng thái: Chờ admin kiểm tra",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.message_handler(commands=['tkh'])
def add_locked_money(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, uid, amount = message.text.split()
        uid = int(uid)
        amount = int(amount)
    except:
        bot.reply_to(message, "Sai cú pháp\n/tkh idtele sotien")
        return

    user = get_user(uid)

    user["locked"] += amount

    bot.send_message(
        message.chat.id,
        f"✅ Đã cộng tiền tạm khóa\n\n"
        f"👤 User: {uid}\n"
        f"🔒 Tiền khóa: +{amount:,}đ"
    )

    bot.send_message(
        uid,
        f"💰 Bạn vừa nhận tiền tạm khóa\n"
        f"🔒 Số tiền: {amount:,}đ"
    )

@bot.message_handler(commands=['chtk'])
def unlock_money(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, uid, amount = message.text.split()
        uid = int(uid)
        amount = int(amount)
    except:
        bot.reply_to(message, "Sai cú pháp\n/chtk idtele sotien")
        return

    user = get_user(uid)

    if user["locked"] < amount:
        bot.reply_to(message, "❌ Không đủ tiền khóa")
        return

    user["locked"] -= amount
    save_data()
    user["balance"] += amount
    save_data()

    bot.send_message(
        message.chat.id,
        f"✅ Đã mở khóa tiền\n\n"
        f"👤 User: {uid}\n"
        f"💰 Tiền rút được: +{amount:,}đ"
    )

    bot.send_message(
        uid,
        f"💵 Tiền của bạn đã được mở khóa\n"
        f"💰 Số tiền: {amount:,}đ"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("duyetwd_"))
def approve_withdraw(call):

    code = call.data.split("_")[1]

    for wd in withdraw_requests:
        if wd["code"] == code and wd["status"] == "pending":

            wd["status"] = "done"

            user = get_user(wd["user_id"])
            user["balance"] = 0

            bot.edit_message_text(
                f"✅ ĐÃ DUYỆT RÚT\n\n"
                f"📄 Mã: {code}\n"
                f"👤 User: {wd['user_id']}\n"
                f"💰 {wd['amount']:,}đ",
                call.message.chat.id,
                call.message.message_id
            )

            bot.send_message(
                wd["user_id"],
                f"🎉 Yêu cầu rút tiền đã được duyệt\n"
                f"💰 Số tiền: {wd['amount']:,}đ"
            )

            return

@bot.callback_query_handler(func=lambda call: call.data.startswith("tuchoiwd_"))
def reject_withdraw(call):

    code = call.data.split("_")[1]

    for wd in withdraw_requests:
        if wd["code"] == code and wd["status"] == "pending":

            wd["status"] = "rejected"

            bot.edit_message_text(
                f"❌ ĐÃ TỪ CHỐI RÚT\n\n"
                f"📄 Mã: {code}\n"
                f"👤 User: {wd['user_id']}",
                call.message.chat.id,
                call.message.message_id
            )

            bot.send_message(
                wd["user_id"],
                "❌ Yêu cầu rút tiền của bạn đã bị từ chối"
            )

            return

@bot.message_handler(func=lambda m: m.text.startswith("/duyetDH"))
def approve_order(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        order_code = message.text.replace("/duyet", "")
    except:
        bot.reply_to(message, "❌ Sai cú pháp\n/duyetDHxxxx")
        return

    for order in orders:

        if order["code"] == order_code and order["status"] == "waiting_check":

            order["status"] = "done"

            user_id = order["user_id"]
            user = get_user(user_id)

            # cập nhật lịch sử user
            for item in user["purchase_history"]:
                if item["code"] == order_code:
                    item["status"] = "Hoàn thành"

            bot.send_message(
                message.chat.id,
                f"✅ ĐÃ DUYỆT ĐƠN\n\n"
                f"📦 Mã đơn: {order_code}"
            )

            bot.send_message(
                user_id,
                f"🎉 Đơn hàng đã được xác nhận\n\n"
                f"📦 Mã đơn: {order_code}\n"
                f"📌 Trạng thái: Hoàn thành"
            )

            return

    bot.reply_to(message, "❌ Không tìm thấy đơn hoặc đơn chưa xác nhận")

@bot.message_handler(commands=['trutien'])
def admin_deduct_money(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        parts = message.text.split(" ", 3)
        uid = int(parts[1])
        amount = int(parts[2])
        reason = parts[3]
    except:
        bot.reply_to(message, "❌ Sai cú pháp\n\n/trutien idtele sotien ly_do")
        return

    user = get_user(uid)

    if user["balance"] < amount:
        bot.reply_to(message, "❌ User không đủ tiền để trừ")
        return

    user["balance"] -= amount

    bot.send_message(
        message.chat.id,
        f"✅ Đã trừ tiền\n\n"
        f"👤 User: {uid}\n"
        f"💸 Số tiền: {amount:,}đ\n"
        f"📄 Lý do: {reason}"
    )

    bot.send_message(
        uid,
        f"⚠️ Tài khoản của bạn vừa bị trừ tiền\n\n"
        f"💸 Số tiền: {amount:,}đ\n"
        f"📄 Lý do: {reason}"
    )

@bot.message_handler(commands=['xemtk'])
def view_account(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        uid = int(message.text.split()[1])
    except:
        bot.reply_to(message, "Sai cú pháp\n/xemtk idtele")
        return

    user = get_user(uid)

    bot.send_message(
        message.chat.id,
        f"👤 USER: {uid}\n\n"
        f"💰 Số dư: {user['balance']:,}đ\n"
        f"🔒 Tiền khóa: {user['locked']:,}đ\n"
        f"📦 Đơn đã tạo: {len(user['purchase_history'])}\n"
        f"📤 Lần rút tiền: {len(user['withdraw_history'])}"
    )

@bot.message_handler(commands=['congtien'])
def add_money(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, uid, amount = message.text.split()
        uid = int(uid)
        amount = int(amount)
    except:
        bot.reply_to(message, "Sai cú pháp\n/congtien idtele sotien")
        return

    user = get_user(uid)
    user["balance"] += amount

    bot.send_message(
        message.chat.id,
        f"✅ Đã cộng tiền\n\n"
        f"👤 User: {uid}\n"
        f"💰 +{amount:,}đ"
    )

    bot.send_message(
        uid,
        f"💰 Bạn vừa nhận tiền\n"
        f"Số tiền: {amount:,}đ"
    )

@bot.message_handler(commands=['block'])
def block_user(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        uid = int(message.text.split()[1])
    except:
        bot.reply_to(message, "Sai cú pháp\n/block idtele")
        return

    blocked_users.add(uid)
    save_data()

    bot.send_message(
        message.chat.id,
        f"🚫 Đã khóa user {uid}"
    )

    bot.send_message(
        uid,
        "🚫 Tài khoản của bạn đã bị khóa."
    )

@bot.message_handler(commands=['unblock'])
def unblock_user(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        uid = int(message.text.split()[1])
    except:
        bot.reply_to(message, "Sai cú pháp\n/unblock idtele")
        return

    blocked_users.discard(uid)
    save_data()

    bot.send_message(
        message.chat.id,
        f"✅ Đã mở khóa user {uid}"
    )

    bot.send_message(
        uid,
        "✅ Tài khoản của bạn đã được mở khóa."
    )

@bot.message_handler(commands=['thongke'])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    total_users = len(users)
    total_orders = len(orders)

    total_balance = sum(u["balance"] for u in users.values())
    total_locked = sum(u["locked"] for u in users.values())

    bot.send_message(
        message.chat.id,
        f"📊 THỐNG KÊ BOT\n\n"
        f"👤 Tổng user: {total_users}\n"
        f"📦 Tổng đơn: {total_orders}\n"
        f"💰 Tổng tiền user: {total_balance:,}đ\n"
        f"🔒 Tổng tiền khóa: {total_locked:,}đ"
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_menu")
def back_menu_inline(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🏠 MENU CHÍNH",
        reply_markup=main_menu(call.from_user.id)
    )
    
load_data()
print("Bot running...")
bot.infinity_polling()
