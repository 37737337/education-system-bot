import telebot
import sqlite3
import random
from telebot import types

TOKEN = "BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

# ================= БАЗА ДАННЫХ =================
conn = sqlite3.connect("school.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    subject TEXT,
    pin TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    name TEXT,
    pin TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS grades (
    student_id INTEGER,
    subject TEXT,
    semester INTEGER,
    grades TEXT,
    comment TEXT
)
""")
conn.commit()

# ---------- преподаватели ----------
teachers = [
    (1, "Иванов И.И.", "Математика", "1111"),
    (2, "Петров П.П.", "Информатика", "2222"),
    (3, "Сидоров С.С.", "Физика", "3333")
]

cursor.execute("SELECT COUNT(*) FROM teachers")
if cursor.fetchone()[0] == 0:
    cursor.executemany("INSERT INTO teachers VALUES (?, ?, ?, ?)", teachers)
    conn.commit()

states = {}

# ================= ВСПОМОГАТЕЛЬНЫЕ =================
def percent(grades):
    return round(sum(grades) / len(grades) / 5 * 100, 1)

def final_mark(p):
    if p <= 54: return 2
    if p <= 69: return 3
    if p <= 84: return 4
    return 5

# ================= МЕНЮ =================
def role_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👨‍🏫 Преподаватель", "👨‍🎓 Ученик")
    return kb

def teacher_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Добавить ученика", "📝 Ввести оценки")
    kb.add("📋 Список учеников", "🚪 Выйти")
    return kb

def student_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Моя успеваемость", "🚪 Выйти")
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    states.clear()
    bot.send_message(m.chat.id, "Выберите роль:", reply_markup=role_menu())

@bot.message_handler(func=lambda m: m.text == "🚪 Выйти")
def logout(m):
    start(m)

# ================= ПРЕПОДАВАТЕЛЬ =================
@bot.message_handler(func=lambda m: m.text == "👨‍🏫 Преподаватель")
def teacher_login(m):
    states[m.chat.id] = {"step": "teacher_pin"}
    bot.send_message(m.chat.id, "Введите PIN преподавателя:")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "teacher_pin")
def teacher_auth(m):
    cursor.execute("SELECT name, subject FROM teachers WHERE pin=?", (m.text,))
    t = cursor.fetchone()
    if not t:
        bot.send_message(m.chat.id, "❌ Неверный PIN")
        return

    states[m.chat.id] = {
        "role": "teacher",
        "name": t[0],
        "subject": t[1]
    }
    bot.send_message(m.chat.id, f"Предмет: {t[1]}", reply_markup=teacher_menu())

# ================= ДОБАВИТЬ УЧЕНИКА =================
@bot.message_handler(func=lambda m: m.text == "👤 Добавить ученика")
def add_student(m):
    states[m.chat.id]["step"] = "add_student"
    bot.send_message(m.chat.id, "Введите ФИО ученика:")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "add_student")
def save_student(m):
    pin = str(random.randint(1000, 9999))
    cursor.execute(
        "INSERT INTO students VALUES (?, ?, ?)",
        (random.randint(100000, 999999), m.text, pin)
    )
    conn.commit()
    states[m.chat.id].pop("step")
    bot.send_message(m.chat.id, f"✅ Ученик добавлен\nPIN: {pin}", reply_markup=teacher_menu())

# ================= СПИСОК УЧЕНИКОВ =================
@bot.message_handler(func=lambda m: m.text == "📋 Список учеников")
def list_students(m):
    cursor.execute("SELECT name, pin FROM students")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "Учеников нет")
        return

    text = "📋 Ученики:\n\n"
    for n, p in rows:
        text += f"{n} — PIN: {p}\n"

    bot.send_message(m.chat.id, text, reply_markup=teacher_menu())

# ================= ОЦЕНКИ =================
@bot.message_handler(func=lambda m: m.text == "📝 Ввести оценки")
def choose_student(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cursor.execute("SELECT name FROM students")
    for s in cursor.fetchall():
        kb.add(s[0])
    kb.add("🚪 Выйти")
    states[m.chat.id]["step"] = "choose_student"
    bot.send_message(m.chat.id, "Выберите ученика:", reply_markup=kb)

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "choose_student")
def choose_semester(m):
    cursor.execute("SELECT id FROM students WHERE name=?", (m.text,))
    st = cursor.fetchone()
    if not st:
        return
    states[m.chat.id]["student_id"] = st[0]
    states[m.chat.id]["step"] = "semester"
    bot.send_message(m.chat.id, "Введите семестр (1 или 2):")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "semester")
def input_grades(m):
    states[m.chat.id]["semester"] = int(m.text)
    states[m.chat.id]["step"] = "grades"
    bot.send_message(m.chat.id, "Введите оценки через запятую:")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "grades")
def input_comment(m):
    states[m.chat.id]["grades"] = m.text.replace(" ", "")
    states[m.chat.id]["step"] = "comment"
    bot.send_message(m.chat.id, "Комментарий:")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "comment")
def save_grades(m):
    cursor.execute(
        "INSERT INTO grades VALUES (?, ?, ?, ?, ?)",
        (
            states[m.chat.id]["student_id"],
            states[m.chat.id]["subject"],
            states[m.chat.id]["semester"],
            states[m.chat.id]["grades"],
            m.text
        )
    )
    conn.commit()
    states[m.chat.id].pop("step")
    bot.send_message(m.chat.id, "✅ Оценки сохранены", reply_markup=teacher_menu())

# ================= УЧЕНИК =================
@bot.message_handler(func=lambda m: m.text == "👨‍🎓 Ученик")
def student_login(m):
    states[m.chat.id] = {"step": "student_pin"}
    bot.send_message(m.chat.id, "Введите PIN ученика:")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "student_pin")
def student_auth(m):
    cursor.execute("SELECT id FROM students WHERE pin=?", (m.text,))
    st = cursor.fetchone()
    if not st:
        bot.send_message(m.chat.id, "❌ Неверный PIN")
        return

    states[m.chat.id] = {"student_id": st[0]}
    bot.send_message(m.chat.id, "Меню ученика", reply_markup=student_menu())

# ================= УСПЕВАЕМОСТЬ =================
@bot.message_handler(func=lambda m: m.text == "📊 Моя успеваемость")
def progress(m):
    cursor.execute(
        "SELECT subject, semester, grades, comment FROM grades WHERE student_id=?",
        (states[m.chat.id]["student_id"],)
    )
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "Оценок пока нет")
        return

    data = {}
    comments = {}

    for subj, sem, g, c in rows:
        key = (subj, sem)
        data.setdefault(key, []).extend(map(int, g.split(",")))
        comments.setdefault(key, []).append(c)

    text = "📊 Успеваемость:\n\n"
    for (subj, sem), grades in data.items():
        p = percent(grades)
        text += (
            f"{subj} — {sem} семестр\n"
            f"Оценки: {','.join(map(str, grades))}\n"
            f"Комментарий: {'; '.join(comments[(subj, sem)])}\n"
            f"Процент: {p}%\n"
            f"Итог: {final_mark(p)}\n\n"
        )

    bot.send_message(m.chat.id, text)

bot.polling()
