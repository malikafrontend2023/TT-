import json
import time
import urllib.request
import urllib.parse
import random
import threading

BOT_TOKEN = "8491606211:AAGah0ZXDWd7_h5jBPkEua0YEgDS2FRBhtY"
GROUP_ID = "-1003859300213"
ADMIN_IDS = [1962559331, 664143932, 1014757198, 634318275, 531433833]

quiz_running = False
stop_event = threading.Event()
quiz_start_time = 0

# {uid: {name, correct, wrong, start_time}}
user_stats = {}

# {poll_id: correct_index}
active_polls = {}

# Bir poll - bir user - bir marta hisoblash uchun
# {uid_pollid: True}
already_answered = {}

with open("quiz_data.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

def get_8_sets():
    q = ALL_QUESTIONS.copy()
    random.shuffle(q)
    sets = {}
    names = ["1-QISM","2-QISM","3-QISM","4-QISM",
             "5-QISM","6-QISM","7-QISM","8-QISM"]
    for i in range(8):
        sets[str(i+1)] = (names[i], q[i*50:(i+1)*50])
    return sets

def api(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"API xato ({method}): {e}")
        return {"ok": False}

def send_message(text, markup=None):
    data = {"chat_id": GROUP_ID, "text": text, "parse_mode": "HTML"}
    if markup:
        data["reply_markup"] = json.dumps(markup)
    return api("sendMessage", data)

def send_quiz_poll(q, current, total):
    # Javoblarni aralashtiramiz
    options = q["options"].copy()
    correct_text = options[q["correct"]]  # To'g'ri javob matni
    random.shuffle(options)
    new_correct_idx = options.index(correct_text)  # Aralashtirdan keyin indeks

    question_text = f"[{current}/{total}] {q['question']}"
    if len(question_text) > 300:
        question_text = question_text[:297] + "..."

    data = {
        "chat_id": GROUP_ID,
        "question": question_text,
        "options": json.dumps(options),
        "type": "quiz",
        "correct_option_id": new_correct_idx,
        "is_anonymous": False,
        "open_period": 30
    }
    result = api("sendPoll", data)
    if result.get("ok"):
        poll_id = result["result"]["poll"]["id"]
        # Shu poll uchun to'g'ri javob indeksini saqlaymiz
        active_polls[poll_id] = new_correct_idx
        print(f"Poll {current}/{total} yuborildi. poll_id={poll_id}, correct={new_correct_idx}")
        return True
    print(f"Poll yuborishda xato: {result}")
    return False

def format_time(seconds):
    seconds = int(seconds)
    m = seconds // 60
    s = seconds % 60
    return f"{m} daq {s} son" if m > 0 else f"{s} son"

def show_results(set_name, elapsed, stopped=False):
    status = "TOXTATILDI" if stopped else "TUGADI"
    text = f"<b>{set_name} - {status}</b>\n"
    text += f"Vaqt: {format_time(elapsed)}\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if not user_stats:
        text += "Hech kim qatnashmadi"
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
            wrong = stat["wrong"]
            total_ans = correct + wrong
            percent = round(correct / total_ans * 100) if total_ans > 0 else 0
            user_elapsed = format_time(stat["elapsed"])
            text += f"{medal} <b>{name}</b>\n"
            text += f"   Togri: {correct} | Xato: {wrong} | Jami: {total_ans} ({percent}%)\n"
            text += f"   Vaqt: {user_elapsed}\n\n"

    send_message(text)

def run_quiz(set_name, qset):
    global quiz_running, user_stats, active_polls, already_answered, quiz_start_time
    stop_event.clear()
    user_stats = {}
    active_polls = {}
    already_answered = {}
    quiz_start_time = time.time()
    total = len(qset)

    send_message(
        f"<b>{set_name} BOSHLANDI</b>\n"
        f"Savollar soni: {total} ta\n"
        f"Har savol uchun: 30 soniya\n"
        f"Toxtatish: STOP yozing\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    time.sleep(2)

    for i, q in enumerate(qset):
        if stop_event.is_set():
            time.sleep(5)  # Oxirgi poll_answer larni yig'ish
            elapsed = time.time() - quiz_start_time
            show_results(set_name, elapsed, stopped=True)
            quiz_running = False
            return

        send_quiz_poll(q, i + 1, total)

        # 30 soniya kutish
        for _ in range(33):
            if stop_event.is_set():
                break
            time.sleep(1)

    # Barcha savollar tugadi
    time.sleep(5)  # Oxirgi poll_answer larni yig'ish
    elapsed = time.time() - quiz_start_time
    show_results(set_name, elapsed, stopped=False)
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
    global user_stats, already_answered

    poll_id = pa.get("poll_id", "")
    user = pa.get("user", {})
    uid = user.get("id")
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    name = f"{first} {last}".strip()
    option_ids = pa.get("option_ids", [])

    print(f"poll_answer: uid={uid}, poll_id={poll_id}, option_ids={option_ids}")
    print(f"active_polls keys: {list(active_polls.keys())[:5]}")

    # Javob bermagan (qaytarib olgan)
    if not option_ids:
        print("option_ids bosh - javob qaytarib olindi")
        return

    # Bu poll bizniki emasmi
    if poll_id not in active_polls:
        print(f"poll_id={poll_id} active_polls da yoq!")
        return

    # Bu user bu pollga allaqachon javob berganmi
    key = f"{uid}_{poll_id}"
    if key in already_answered:
        print(f"User {uid} bu pollga allaqachon javob bergan")
        return
    already_answered[key] = True

    chosen = option_ids[0]
    correct = active_polls[poll_id]
    is_correct = (chosen == correct)
    now = time.time()

    print(f"User {name}: tanlagan={chosen}, togri={correct}, natija={'TOGRI' if is_correct else 'XATO'}")

    if uid not in user_stats:
        user_stats[uid] = {
            "name": name,
            "correct": 0,
            "wrong": 0,
            "start_time": now,
            "elapsed": 0
        }

    if is_correct:
        user_stats[uid]["correct"] += 1
    else:
        user_stats[uid]["wrong"] += 1

    user_stats[uid]["elapsed"] = now - user_stats[uid]["start_time"]

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

    t = text.lower()

    if "/start" in t or "/menu" in t:
        send_message("<b>Quiz boshqaruvi</b>\nQaysi qismni boshlaysiz?", admin_menu())

    elif "stop" in t:
        if quiz_running:
            stop_event.set()
            send_message("Toxtatilmoqda... 5 soniyadan keyin natija chiqadi")
        else:
            send_message("Hozir aktiv quiz yoq")

    else:
        chosen_set = None
        for i in range(1, 9):
            if f"{i}-qism" in t or f"/set{i}" in t:
                chosen_set = str(i)
                break

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
