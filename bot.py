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
active_polls = {}  # poll_id -> correct_option_id

with open("quiz_data.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

def get_8_sets():
    q = ALL_QUESTIONS.copy()
    random.shuffle(q)
    sets = {}
    names = [
        "1-QISM", "2-QISM", "3-QISM", "4-QISM",
        "5-QISM", "6-QISM", "7-QISM", "8-QISM"
    ]
    for i in range(8):
        start = i * 50
        end = start + 50
        sets[str(i+1)] = (names[i], q[start:end])
    return sets

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

def send_quiz_poll(q, current, total):
    options = q["options"].copy()
    correct_text = options[q["correct"]]
    random.shuffle(options)
    new_correct = options.index(correct_text)

    question_text = f"[{current}/{total}] {q['question']}"
    if len(question_text) > 300:
        question_text = question_text[:297] + "..."

    data = {
        "chat_id": GROUP_ID,
        "question": question_text,
        "options": json.dumps(options),
        "type": "quiz",
        "correct_option_id": new_correct,
        "is_anonymous": False,
        "open_period": 30
    }
    result = api("sendPoll", data)
    if result.get("ok"):
        poll_id = result["result"]["poll"]["id"]
        active_polls[poll_id] = new_correct
        return poll_id
    return None

def format_time(seconds):
    seconds = int(seconds)
    m = seconds // 60
    s = seconds % 60
    return f"{m} daq {s} son" if m > 0 else f"{s} son"

def show_results(set_name, start_time, stopped=False):
    elapsed = time.time() - start_time
    status = "TO'XTATILDI" if stopped else "TUGADI"

    text = f"<b>{set_name} — {status}</b>\n"
    text += f"⏱ Umumiy vaqt: {format_time(elapsed)}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    if not user_stats:
        text += "😕 Hech kim qatnashmadi"
    else:
        sorted_users = sorted(
            user_stats.items(),
            key=lambda x: x[1]["correct"],
            reverse=True
        )
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, stat) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = stat["name"]
            correct = stat["correct"]
            total = stat["answered"]
            percent = round(correct / total * 100) if total > 0 else 0
            user_time = format_time(stat["elapsed"])
            text += f"{medal} <b>{name}</b>\n"
            text += f"   {correct}/{total} togri ({percent}%) | {user_time}\n\n"

    send_message(text)

def run_quiz(set_name, qset):
    global quiz_running, user_stats, active_polls
    stop_event.clear()
    user_stats = {}
    active_polls = {}
    start_time = time.time()
    total = len(qset)

    send_message(
        f"<b>{set_name} BOSHLANDI!</b>\n"
        f"Savollar: {total} ta\n"
        f"Har savol uchun 30 soniya\n"
        f"Toxtatish: /stop\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    time.sleep(2)

    for i, q in enumerate(qset):
        if stop_event.is_set():
            show_results(set_name, start_time, stopped=True)
            quiz_running = False
            return

        send_quiz_poll(q, i + 1, total)

        for _ in range(33):
            if stop_event.is_set():
                break
            time.sleep(1)

    show_results(set_name, start_time, stopped=False)
    active_polls = {}
    quiz_running = False

def admin_menu():
    return {
        "keyboard": [
            [{"text": "1-qism"}, {"text": "2-qism"}],
            [{"text": "3-qism"}, {"text": "4-qism"}],
            [{"text": "5-qism"}, {"text": "6-qism"}],
            [{"text": "7-qism"}, {"text": "8-qism"}],
            [{"text": "STOP"}]
        ],
        "resize_keyboard": True
    }

def handle_poll_answer(pa):
    poll_id = pa.get("poll_id")
    user = pa.get("user", {})
    uid = user.get("id")
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    option_ids = pa.get("option_ids", [])

    if not option_ids:
        return

    chosen = option_ids[0]
    correct = active_polls.get(poll_id)
    if correct is None:
        return

    is_correct = (chosen == correct)
    now = time.time()

    if uid not in user_stats:
        user_stats[uid] = {
            "name": name,
            "correct": 0,
            "answered": 0,
            "start_time": now,
            "elapsed": 0
        }

    user_stats[uid]["answered"] += 1
    user_stats[uid]["elapsed"] = now - user_stats[uid]["start_time"]
    if is_correct:
        user_stats[uid]["correct"] += 1

def is_stop(text):
    t = text.lower().strip()
    return "stop" in t or "/stop" in t

def is_start(text):
    return "/start" in text or "/menu" in text

def get_set_number(text):
    for i in range(1, 9):
        if f"{i}-qism" in text or f"/set{i}" in text:
            return str(i)
    return None

def handle_update(update):
    global quiz_running

    if "poll_answer" in update:
        handle_poll_answer(update["poll_answer"])
        return

    msg = update.get("message")
    if not msg:
        return

    uid = msg.get("from", {}).get("id")
    text = (msg.get("text") or "").strip()

    if uid not in ADMIN_IDS:
        return

    if is_start(text):
        send_message("<b>Quiz boshqaruvi</b>\nQaysi qismni boshlaysiz?", admin_menu())

    elif is_stop(text):
        if quiz_running:
            stop_event.set()
            send_message("Toxtatilmoqda, natijalar hisoblanmoqda...")
        else:
            send_message("Hozir aktiv quiz yoq!")

    else:
        chosen_set = get_set_number(text)
        if chosen_set:
            if quiz_running:
                send_message("Avval STOP bering!")
                return
            sets = get_8_sets()
            set_name, qset = sets[chosen_set]
            quiz_running = True
            threading.Thread(
                target=run_quiz,
                args=(set_name, qset),
                daemon=True
            ).start()

def main():
    print("Bot ishga tushdi!")
    offset = 0
    while True:
        try:
            url = (
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
                f"?offset={offset}&timeout=30"
                f"&allowed_updates=%5B%22message%22%2C%22poll_answer%22%5D"
            )
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
