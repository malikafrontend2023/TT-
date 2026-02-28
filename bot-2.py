import json
import time
import urllib.request
import urllib.parse
import random
import threading

BOT_TOKEN = "8491606211:AAGah0ZXDWd7_h5jBPkEua0YEgDS2FRBhtY"
GROUP_ID = "-1003859300213"
ADMIN_IDS = [1962559331, 664143932, 1014757198]

quiz_running = False
stop_event = threading.Event()
user_stats = {}

with open("quiz_data.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

def get_sets():
    q = ALL_QUESTIONS.copy()
    random.shuffle(q)
    return {
        "1": ("1-QISM (1-100)", q[0:100]),
        "2": ("2-QISM (101-200)", q[100:200]),
        "3": ("3-QISM (201-300)", q[200:300]),
        "4": ("4-QISM (301-395)", q[300:]),
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

def send_message(text, markup=None):
    data = {"chat_id": GROUP_ID, "text": text, "parse_mode": "HTML"}
    if markup:
        data["reply_markup"] = json.dumps(markup)
    return api("sendMessage", data)

def send_quiz_poll(q):
    options = q["options"].copy()
    correct_text = options[q["correct"]]
    random.shuffle(options)
    new_correct = options.index(correct_text)
    data = {
        "chat_id": GROUP_ID,
        "question": q["question"][:300],
        "options": json.dumps(options),
        "type": "quiz",
        "correct_option_id": new_correct,
        "is_anonymous": False,
        "open_period": 30
    }
    return api("sendPoll", data)

def format_time(seconds):
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m} daq {s} son" if m > 0 else f"{s} soniya"

def show_results(set_name, start_time, stopped=False):
    elapsed = time.time() - start_time
    status = "TO'XTATILDI 🛑" if stopped else "TUGADI 🏁"

    text = f"<b>{set_name} — {status}</b>\n"
    text += f"⏱ Vaqt: {format_time(elapsed)}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    if not user_stats:
        text += "😕 Hech kim qatnashmadi"
    else:
        sorted_users = sorted(user_stats.items(),
                              key=lambda x: x[1]["total"], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, stat) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = stat["name"]
            total = stat["total"]
            user_time = format_time(stat["elapsed"])
            text += f"{medal} <b>{name}</b> — {total} ta javob | ⏱ {user_time}\n"

    send_message(text)

def run_quiz(set_name, qset):
    global quiz_running, user_stats
    stop_event.clear()
    user_stats = {}
    start_time = time.time()

    send_message(
        f"📚 <b>{set_name} BOSHLANDI!</b>\n"
        f"📝 Savollar: {len(qset)} ta\n"
        f"⏱ Har savol uchun 30 soniya\n"
        f"🛑 To'xtatish: /stop\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    time.sleep(2)

    for i, q in enumerate(qset):
        if stop_event.is_set():
            show_results(set_name, start_time, stopped=True)
            quiz_running = False
            return
        send_quiz_poll(q)
        for _ in range(33):
            if stop_event.is_set():
                break
            time.sleep(1)

    show_results(set_name, start_time, stopped=False)
    quiz_running = False

def admin_menu():
    return {
        "keyboard": [
            [{"text": "▶️ 1-qism"}, {"text": "▶️ 2-qism"}],
            [{"text": "▶️ 3-qism"}, {"text": "▶️ 4-qism"}],
            [{"text": "🛑 To'xtatish"}]
        ],
        "resize_keyboard": True
    }

def handle_poll_answer(pa):
    user = pa.get("user", {})
    uid = user.get("id")
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    if uid not in user_stats:
        user_stats[uid] = {"name": name, "total": 0,
                           "start_time": time.time(), "elapsed": 0}
    user_stats[uid]["total"] += 1
    user_stats[uid]["elapsed"] = time.time() - user_stats[uid]["start_time"]

def handle_update(update):
    global quiz_running

    if "poll_answer" in update:
        handle_poll_answer(update["poll_answer"])
        return

    msg = update.get("message")
    if not msg:
        return

    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "")

    if uid not in ADMIN_IDS:
        return

    if text in ["/start", "/menu"]:
        send_message("👋 <b>Quiz boshqaruvi</b>\nQaysi qismni boshlaysiz?", admin_menu())

    elif "1-qism" in text or text == "/set1":
        if quiz_running:
            send_message("⚠️ Avval /stop bilan to'xtating!")
            return
        sets = get_sets()
        name, qset = sets["1"]
        quiz_running = True
        threading.Thread(target=run_quiz, args=(name, qset), daemon=True).start()

    elif "2-qism" in text or text == "/set2":
        if quiz_running:
            send_message("⚠️ Avval /stop bilan to'xtating!")
            return
        sets = get_sets()
        name, qset = sets["2"]
        quiz_running = True
        threading.Thread(target=run_quiz, args=(name, qset), daemon=True).start()

    elif "3-qism" in text or text == "/set3":
        if quiz_running:
            send_message("⚠️ Avval /stop bilan to'xtating!")
            return
        sets = get_sets()
        name, qset = sets["3"]
        quiz_running = True
        threading.Thread(target=run_quiz, args=(name, qset), daemon=True).start()

    elif "4-qism" in text or text == "/set4":
        if quiz_running:
            send_message("⚠️ Avval /stop bilan to'xtating!")
            return
        sets = get_sets()
        name, qset = sets["4"]
        quiz_running = True
        threading.Thread(target=run_quiz, args=(name, qset), daemon=True).start()

    elif "To'xtatish" in text or text == "/stop":
        if quiz_running:
            stop_event.set()
            send_message("🛑 To'xtatilmoqda, natijalar tayorlanmoqda...")
        else:
            send_message("⚠️ Hozir aktiv quiz yo'q!")

def main():
    print("Bot ishga tushdi! ✅")
    offset = 0
    while True:
        try:
            url = (f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
                   f"?offset={offset}&timeout=30"
                   f"&allowed_updates=%5B%22message%22%2C%22poll_answer%22%5D")
            with urllib.request.urlopen(url, timeout=35) as resp:
                data = json.loads(resp.read())
            if data.get("ok"):
                for upd in data["result"]:
                    offset = upd["update_id"] + 1
                    handle_update(upd)
        except Exception as e:
            print(f"Xato: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
