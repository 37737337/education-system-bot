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
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    name TEXT,
    pin TEXT
)
""")

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

# ================= SEED =================
cursor.execute("SELECT COUNT(*) FROM admins")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO admins VALUES (1, 'Администратор', '9999')")

cursor.execute("SELECT COUNT(*) FROM teachers")
if cursor.fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO teachers VALUES (?, ?, ?, ?)",
        [
            (1, "Иванов И.И.", "Математика", "1111"),
            (2, "Петров П.П.", "Информатика", "2222"),
        ]
    )
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
    kb.add("🛠 Администратор", "👨‍🏫 Преподаватель", "👨‍🎓 Ученик")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить преподавателя", "📋 Список преподавателей")
    kb.add("❌ Удалить преподавателя", "🚪 Выйти")
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

# ================= АДМИНИСТРАТОР =================
@bot.message_handler(func=lambda m: m.text == "🛠 Администратор")
def admin_login(m):
    states[m.chat.id] = {"step": "admin_pin"}
    bot.send_message(m.chat.id, "Введите PIN администратора:")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "admin_pin")
def admin_auth(m):
    cursor.execute("SELECT name FROM admins WHERE pin=?", (m.text,))
    admin = cursor.fetchone()
    if not admin:
        bot.send_message(m.chat.id, "❌ Неверный PIN")
        return

    states[m.chat.id] = {"role": "admin"}
    bot.send_message(m.chat.id, "Меню администратора", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить преподавателя")
def add_teacher(m):
    states[m.chat.id]["step"] = "add_teacher"
    bot.send_message(m.chat.id, "Введите: ФИО, Предмет (через запятую)")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "add_teacher")
def save_teacher(m):
    name, subject = map(str.strip, m.text.split(","))
    pin = str(random.randint(1000, 9999))
    cursor.execute(
        "INSERT INTO teachers VALUES (?, ?, ?, ?)",
        (random.randint(100,999), name, subject, pin)
    )
    conn.commit()
    states[m.chat.id].pop("step")
    bot.send_message(m.chat.id, f"✅ Преподаватель добавлен\nPIN: {pin}", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📋 Список преподавателей")
def list_teachers(m):
    cursor.execute("SELECT name, subject, pin FROM teachers")
    rows = cursor.fetchall()
    text = "📋 Преподаватели:\n\n"
    for n,s,p in rows:
        text += f"{n} — {s} — PIN: {p}\n"
    bot.send_message(m.chat.id, text, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "❌ Удалить преподавателя")
def del_teacher_start(m):
    states[m.chat.id]["step"] = "del_teacher"
    bot.send_message(m.chat.id, "Введите PIN преподавателя:")

@bot.message_handler(func=lambda m: states.get(m.chat.id, {}).get("step") == "del_teacher")
def del_teacher(m):
    cursor.execute("DELETE FROM teachers WHERE pin=?", (m.text,))
    conn.commit()
    states[m.chat.id].pop("step")
    bot.send_message(m.chat.id, "✅ Преподаватель удалён", reply_markup=admin_menu())

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

    states[m.chat.id] = {"role":"teacher","name":t[0],"subject":t[1]}
    bot.send_message(m.chat.id, f"Предмет: {t[1]}", reply_markup=teacher_menu())

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

