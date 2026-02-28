import json
import time
import urllib.request
import urllib.parse
import random
import threading
import os

BOT_TOKEN = "8491606211:AAGah0ZXDWd7_h5jBPkEua0YEgDS2FRBhtY"
CHAT_ID = "-1003859300213"

# Admin Telegram ID lari (o'zingiznikini qo'shing)
ADMIN_IDS = [1962559331]

# Global holat
quiz_running = False
quiz_thread = None
stop_event = threading.Event()

# Savollarni yuklash
with open("quiz_data.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

# 4 ta to'plam (har safar aralashtiriladi)
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
    data = {"chat_id": chat_id, "text": text}
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
    return api("sendPoll", data)

def run_quiz(set_num, qset):
    global quiz_running
    stop_event.clear()

    send_message(CHAT_ID,
        f"📚 {set_num}-QISM BOSHLANDI!\n"
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
                f"🛑 {set_num}-QISM TO'XTATILDI!\n"
                f"✅ {ok}/{len(qset)} savol yuborildi"
            )
            quiz_running = False
            return

        result = send_quiz_poll(q)
        if result.get("ok"):
            ok += 1
            print(f"✅ {set_num}-qism: {i+1}/{len(qset)}")
        else:
            print(f"❌ {set_num}-qism: {i+1} xato")

        # 30 soniya kutish (to'xtatilsa chiqadi)
        for _ in range(33):
            if stop_event.is_set():
                break
            time.sleep(1)

    send_message(CHAT_ID,
        f"🏁 {set_num}-QISM TUGADI!\n"
        f"✅ {ok}/{len(qset)} savol yuborildi\n"
        f"📊 Natijalar yuqoridagi savollarda ko'rinadi\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    quiz_running = False

def admin_keyboard():
    return {
        "keyboard": [
            [{"text": "▶️ 1-qism (1-100)"},  {"text": "▶️ 2-qism (101-200)"}],
            [{"text": "▶️ 3-qism (201-300)"}, {"text": "▶️ 4-qism (301-395)"}],
            [{"text": "🛑 To'xtatish"}]
        ],
        "resize_keyboard": True
    }

def handle_update(update):
    global quiz_running, quiz_thread

    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return

    user_id = msg.get("from", {}).get("id")
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")

    # Faqat adminlar uchun
    if user_id not in ADMIN_IDS:
        return

    if text in ["/start", "/menu"]:
        send_message(chat_id,
            "👋 Salom! Quiz boshqaruvi:\n\n"
            "▶️ Qaysi qismni boshlashni tanlang:",
            admin_keyboard()
        )

    elif "1-qism" in text or text == "/set1":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        quiz_thread = threading.Thread(target=run_quiz, args=("1", sets["1"]))
        quiz_thread.daemon = True
        quiz_thread.start()

    elif "2-qism" in text or text == "/set2":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        quiz_thread = threading.Thread(target=run_quiz, args=("2", sets["2"]))
        quiz_thread.daemon = True
        quiz_thread.start()

    elif "3-qism" in text or text == "/set3":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        quiz_thread = threading.Thread(target=run_quiz, args=("3", sets["3"]))
        quiz_thread.daemon = True
        quiz_thread.start()

    elif "4-qism" in text or text == "/set4":
        if quiz_running:
            send_message(chat_id, "⚠️ Avval joriy quizni to'xtating! /stop")
            return
        sets = get_sets()
        quiz_running = True
        quiz_thread = threading.Thread(target=run_quiz, args=("4", sets["4"]))
        quiz_thread.daemon = True
        quiz_thread.start()

    elif "To'xtatish" in text or text == "/stop":
        if quiz_running:
            stop_event.set()
            send_message(chat_id, "🛑 To'xtatilmoqda...")
        else:
            send_message(chat_id, "⚠️ Hozir aktiv quiz yo'q!")

# Long polling
def main():
    print("Bot ishga tushdi! ✅")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
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
