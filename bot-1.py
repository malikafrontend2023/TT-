import json
import time
import urllib.request
import urllib.parse
import random
import threading

BOT_TOKEN = "8491606211:AAGah0ZXDWd7_h5jBPkEua0YEgDS2FRBhtY"
CHAT_ID = "-1003859300213"
ADMIN_IDS = [1962559331, 664143932, 1014757198]

# Global holat
quiz_running = False
stop_event = threading.Event()

# Har kimning natijasi: {user_id: {"name": ..., "correct": 0, "total": 0, "start_time": ...}}
user_stats = {}

with open("quiz_data.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

def get_sets():
    questions = ALL_QUESTIONS.copy()
    random.shuffle(questions)
    return {
        "1": questions[0:100],
        "2": questions[100:200],
        "3": questions[200:300],
        "4": questions[300:],
    }

def api(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded,
          headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except:
        return {"ok": False}

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return api("sendMessage", data)

def send_quiz_poll(q):
    options = q["options"].copy()
    correct_text = options[q["correct"]]
    random.shuffle(options)
    new_correct = options.index(correct_text)
    data = {
        "chat_id": CHAT_ID,
        "question": q["question"][:300],
        "options": json.dumps(options),
        "type": "quiz",
        "correct_option_id": new_correct,
        "is_anonymous": False,
        "open_period": 30
    }
    result = api("sendPoll", data)
    if result.get("ok"):
        return result["result"]["poll"]["id"], new_correct
    return None, new_correct

def format_duration(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    if minutes > 0:
        return f"{minutes} daqiqa {secs} soniya"
    return f"{secs} soniya"

def send_results(set_num, qset_len, start_time):
    elapsed = time.time() - start_time
    duration_str = format_duration(elapsed)

    if not user_stats:
        send_message(CHAT_ID,
            f"🏁 <b>{set_num}-QISM TUGADI!</b>\n\n"
            f"😕 Hech kim qatnashmadi\n"
            f"⏱ Vaqt: {duration_str}"
        )
        return

    # Saralash: to'g'ri javoblar bo'yicha
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1]["correct"], reverse=True)

    result_text = f"🏁 <b>{set_num}-QISM NATIJALARI</b>\n"
    result_text += f"⏱ Umumiy vaqt: {duration_str}\n"
    result_text += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, stat) in enumerate(sorted_users):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = stat.get("name", "Noma'lum")
        correct = stat["correct"]
        total = stat["total"]
        percent = round(correct / total * 100) if total > 0 else 0
        user_time = format_duration(stat.get("elapsed", 0))
        result_text += f"{medal} <b>{name}</b>\n"
        result_text += f"   ✅ {correct}/{total} ({percent}%) — ⏱ {user_time}\n\n"

    send_message(CHAT_ID, result_text)

def run_quiz(set_num, qset):
    global quiz_running, user_stats
    stop_event.clear()
    user_stats = {}
    start_time = time.time()

    send_message(CHAT_ID,
        f"📚 <b>{set_num}-QISM BOSHLANDI!</b>\n"
        f"📝 Savollar: {len(qset)} ta\n"
        f"⏱ Har savol uchun 30 soniya\n"
        f"🛑 To'xtatish: /stop\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    time.sleep(2)

    ok = 0
    for i, q in enumerate(qset):
        if stop_event.is_set():
            send_message(CHAT_ID,
                f"🛑 <b>{set_num}-QISM TO'XTATILDI!</b>\n"
                f"✅ {ok}/{len(qset)} savol yuborildi"
            )
            send_results(set_num, len(qset), start_time)
            quiz_running = False
            return

        poll_id, correct_idx = send_quiz_poll(q)
        if poll_id:
            ok += 1

        for _ in range(33):
            if stop_event.is_set():
                break
            time.sleep(1)

    send_results(set_num, len(qset), start_time)
    quiz_running = False

def admin_keyboard():
    return {
        "keyboard": [
            [{"text": "▶️ 1-qism (1-100)"}, {"text": "▶️ 2-qism (101-200)"}],
            [{"text": "▶️ 3-qism (201-300)"}, {"text": "▶️ 4-qism (301-395)"}],
            [{"text": "🛑 To'xtatish"}]
        ],
        "resize_keyboard": True
    }

def handle_poll_answer(poll_answer):
    user = poll_answer.get("user", {})
    user_id = user.get("id")
    name = user.get("first_name", "")
    last = user.get("last_name", "")
    full_name = f"{name} {last}".strip()

    if user_id not in user_stats:
        user_stats[user_id] = {
            "name": full_name,
            "correct": 0,
            "total": 0,
            "start_time": time.time(),
            "elapsed": 0
        }

    user_stats[user_id]["total"] += 1
    user_stats[user_id]["elapsed"] = time.time() - user_stats[user_id]["start_time"]

    # Telegram poll_answer da to'g'ri javob ma'lumoti yo'q
    # Shuning uchun faqat qatnashganini hisoblaymiz
    # To'g'ri javobni Telegram o'zi ko'rsatadi pollda

def handle_update(update):
    global quiz_running

    # Poll javoblari
    if "poll_answer" in update:
        handle_poll_answer(update["poll_answer"])
        return

    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return

    user_id = msg.get("from", {}).get("id")
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")

    if user_id not in ADMIN_IDS:
        return

    if text in ["/start", "/menu"]:
        send_message(chat_id,
            "👋 <b>Quiz boshqaruvi</b>\n\nQaysi qismni boshlashni tanlang:",
            admin_keyboard()
        )

    elif "1-qism" in text or text == "/set1":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        t = threading.Thread(target=run_quiz, args=("1", sets["1"]))
        t.daemon = True
        t.start()

    elif "2-qism" in text or text == "/set2":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        t = threading.Thread(target=run_quiz, args=("2", sets["2"]))
        t.daemon = True
        t.start()

    elif "3-qism" in text or text == "/set3":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        t = threading.Thread(target=run_quiz, args=("3", sets["3"]))
        t.daemon = True
        t.start()

    elif "4-qism" in text or text == "/set4":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        t = threading.Thread(target=run_quiz, args=("4", sets["4"]))
        t.daemon = True
        t.start()

    elif "To'xtatish" in text or text == "/stop":
        if quiz_running:
            stop_event.set()
            send_message(chat_id, "🛑 To'xtatilmoqda...")
        else:
            send_message(chat_id, "⚠️ Hozir aktiv quiz yo'q!")

def main():
    print("Bot ishga tushdi! ✅")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30&allowed_updates=[\"message\",\"poll_answer\"]"
            with urllib.request.urlopen(url, timeout=35) as resp:
                data = json.loads(resp.read())
            if data.get("ok"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    handle_update(update)
        except Exception as e:
            print(f"Xato: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
