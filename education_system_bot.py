import os
import sqlite3
import random
import string
import telebot
from telebot import types
from dotenv import load_dotenv

# ================== CONFIG ==================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found")

bot = telebot.TeleBot(BOT_TOKEN)

# ================== BUTTONS ==================
BTN_ADMIN = "🛠 Администратор"
BTN_TEACHER = "👨‍🏫 Преподаватель"
BTN_STUDENT = "👨‍🎓 Ученик"

BTN_ADD_STUDENT = "👤 Добавить ученика"
BTN_ENTER_GRADES = "✏️ Ввести оценки"
BTN_LIST_STUDENTS = "📋 Список учеников"

BTN_ADD_TEACHER = "➕ Добавить преподавателя"
BTN_LIST_TEACHERS = "📋 Список преподавателей"
BTN_DELETE_PROFILE = "🗑 Удалить профиль"

BTN_PROGRESS = "📊 Моя успеваемость"
BTN_CHANGE_PASSWORD = "🔐 Сменить пароль"
BTN_EXIT = "🚪 Выйти"

# ================== DATABASE ==================
conn = sqlite3.connect("school.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY,
    login TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY,
    login TEXT,
    subject TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY,
    login TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS grades(
    student_id INTEGER,
    subject TEXT,
    semester INTEGER,
    grades TEXT,
    comment TEXT
)
""")
conn.commit()

# ================== SEED ==================
cursor.execute("SELECT COUNT(*) FROM admins")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO admins VALUES (1,'admin','admin123')")

conn.commit()

# ================== STATE ==================
states = {}

def state(chat_id):
    return states.setdefault(chat_id, {"role": None, "step": None})

def reset_step(chat_id):
    states[chat_id]["step"] = None

# ================== UTILS ==================
def gen_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def percent(grades):
    return round(sum(grades) / len(grades) / 5 * 100, 1)

def final_mark(p):
    if p <= 54: return 2
    if p <= 69: return 3
    if p <= 84: return 4
    return 5

def validate_grades(text):
    try:
        grades = list(map(int, text.split(",")))
        if all(2 <= g <= 5 for g in grades):
            return grades
    except:
        pass
    return None

# ================== MENUS ==================
def role_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_ADMIN, BTN_TEACHER, BTN_STUDENT)
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_ADD_TEACHER, BTN_LIST_TEACHERS)
    kb.add(BTN_DELETE_PROFILE)
    kb.add(BTN_EXIT)
    return kb

def teacher_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_ADD_STUDENT)
    kb.add(BTN_ENTER_GRADES)
    kb.add(BTN_LIST_STUDENTS)
    kb.add(BTN_EXIT)
    return kb

def student_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_PROGRESS)
    kb.add(BTN_CHANGE_PASSWORD)
    kb.add(BTN_EXIT)
    return kb

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(m):
    s = state(m.chat.id)
    s["role"] = None
    s["step"] = None
    bot.send_message(m.chat.id, "Выберите роль:", reply_markup=role_menu())

@bot.message_handler(func=lambda m: m.text == BTN_EXIT)
def exit_menu(m):
    start(m)

# ================== ADMIN ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADMIN)
def admin_login(m):
    s = state(m.chat.id)
    s["step"] = "admin_login"
    bot.send_message(m.chat.id, "Введите логин администратора:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "admin_login")
def admin_password(m):
    s = state(m.chat.id)
    s["login"] = m.text
    s["step"] = "admin_password"
    bot.send_message(m.chat.id, "Введите пароль:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "admin_password")
def admin_auth(m):
    s = state(m.chat.id)
    cursor.execute(
        "SELECT id FROM admins WHERE login=? AND password=?",
        (s["login"], m.text)
    )
    if not cursor.fetchone():
        bot.send_message(m.chat.id, "❌ Неверные данные")
        return
    s["role"] = "admin"
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "Меню администратора", reply_markup=admin_menu())

# ================== ADMIN DELETE ==================
@bot.message_handler(func=lambda m: m.text == BTN_DELETE_PROFILE)
def admin_delete(m):
    s = state(m.chat.id)
    if s["role"] != "admin":
        return
    s["step"] = "delete_login"
    bot.send_message(m.chat.id, "Введите логин (ФИО) для удаления:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "delete_login")
def admin_delete_confirm(m):
    cursor.execute("DELETE FROM students WHERE login=?", (m.text,))
    cursor.execute("DELETE FROM teachers WHERE login=?", (m.text,))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Профиль удалён", reply_markup=admin_menu())

# ================== TEACHER ==================
@bot.message_handler(func=lambda m: m.text == BTN_TEACHER)
def teacher_login(m):
    s = state(m.chat.id)
    s["step"] = "teacher_login"
    bot.send_message(m.chat.id, "Введите логин (ФИО):")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "teacher_login")
def teacher_password(m):
    s = state(m.chat.id)
    s["login"] = m.text
    s["step"] = "teacher_password"
    bot.send_message(m.chat.id, "Введите пароль:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "teacher_password")
def teacher_auth(m):
    s = state(m.chat.id)
    cursor.execute(
        "SELECT id, subject FROM teachers WHERE login=? AND password=?",
        (s["login"], m.text)
    )
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Неверные данные")
        return
    s.update({"role":"teacher","subject":row[1],"step":None})
    bot.send_message(m.chat.id, f"Предмет: {row[1]}", reply_markup=teacher_menu())

# ================== ADD STUDENT ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADD_STUDENT)
def add_student(m):
    s = state(m.chat.id)
    if s["role"] != "teacher":
        return
    s["step"] = "student_name"
    bot.send_message(m.chat.id, "Введите ФИО ученика:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "student_name")
def save_student(m):
    password = gen_password()
    cursor.execute(
        "INSERT INTO students VALUES (?,?,?)",
        (random.randint(100000,999999), m.text, password)
    )
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ Ученик добавлен\nЛогин: {m.text}\nПароль: {password}",
        reply_markup=teacher_menu()
    )

# ================== ENTER GRADES ==================
@bot.message_handler(func=lambda m: m.text == BTN_ENTER_GRADES)
def start_grades(m):
    s = state(m.chat.id)
    if s["role"] != "teacher":
        return
    cursor.execute("SELECT login FROM students")
    students = cursor.fetchall()
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for (name,) in students:
        kb.add(name)
    kb.add(BTN_EXIT)
    s["step"] = "choose_student"
    bot.send_message(m.chat.id, "Выберите ученика:", reply_markup=kb)

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "choose_student")
def choose_student(m):
    cursor.execute("SELECT id FROM students WHERE login=?", (m.text,))
    row = cursor.fetchone()
    if not row:
        return
    s = state(m.chat.id)
    s["student_id"] = row[0]
    s["step"] = "semester"
    bot.send_message(m.chat.id, "Введите семестр (1 или 2):")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "semester")
def enter_semester(m):
    if m.text not in ("1","2"):
        bot.send_message(m.chat.id, "Введите 1 или 2")
        return
    s = state(m.chat.id)
    s["semester"] = int(m.text)
    s["step"] = "grades"
    bot.send_message(m.chat.id, "Введите оценки (2–5) через запятую:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "grades")
def enter_grades(m):
    grades = validate_grades(m.text)
    if not grades:
        bot.send_message(m.chat.id, "❌ Оценки должны быть от 2 до 5")
        return
    s = state(m.chat.id)
    s["grades"] = ",".join(map(str, grades))
    s["step"] = "comment"
    bot.send_message(m.chat.id, "Комментарий:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "comment")
def save_grades(m):
    s = state(m.chat.id)
    cursor.execute(
        "INSERT INTO grades VALUES (?,?,?,?,?)",
        (s["student_id"], s["subject"], s["semester"], s["grades"], m.text)
    )
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Оценки сохранены", reply_markup=teacher_menu())

# ================== STUDENT ==================
@bot.message_handler(func=lambda m: m.text == BTN_STUDENT)
def student_login(m):
    s = state(m.chat.id)
    s["step"] = "student_login"
    bot.send_message(m.chat.id, "Введите логин (ФИО):")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "student_login")
def student_password(m):
    s = state(m.chat.id)
    s["login"] = m.text
    s["step"] = "student_password"
    bot.send_message(m.chat.id, "Введите пароль:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "student_password")
def student_auth(m):
    s = state(m.chat.id)
    cursor.execute(
        "SELECT id FROM students WHERE login=? AND password=?",
        (s["login"], m.text)
    )
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Неверные данные")
        return
    s.update({"role":"student","student_id":row[0],"step":None})
    bot.send_message(m.chat.id, "Меню ученика", reply_markup=student_menu())

@bot.message_handler(func=lambda m: m.text == BTN_CHANGE_PASSWORD)
def change_password(m):
    s = state(m.chat.id)
    if s["role"] != "student":
        return
    s["step"] = "new_password"
    bot.send_message(m.chat.id, "Введите новый пароль:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "new_password")
def save_new_password(m):
    s = state(m.chat.id)
    cursor.execute(
        "UPDATE students SET password=? WHERE id=?",
        (m.text, s["student_id"])
    )
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Пароль изменён", reply_markup=student_menu())

@bot.message_handler(func=lambda m: m.text == BTN_PROGRESS)
def progress(m):
    s = state(m.chat.id)
    cursor.execute(
        "SELECT subject, semester, grades, comment FROM grades WHERE student_id=?",
        (s["student_id"],)
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

# ================== RUN ==================
bot.polling()
