import os
import sqlite3
import random
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

BTN_PROGRESS = "📊 Моя успеваемость"
BTN_EXIT = "🚪 Выйти"

# ================== DATABASE ==================
conn = sqlite3.connect("school.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY, name TEXT, pin TEXT)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY, name TEXT, subject TEXT, pin TEXT)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY, name TEXT, pin TEXT)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS grades(
    student_id INTEGER, subject TEXT, semester INTEGER, grades TEXT, comment TEXT)""")

conn.commit()

# ================== SEED ==================
cursor.execute("SELECT COUNT(*) FROM admins")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO admins VALUES (1,'Администратор','9999')")

cursor.execute("SELECT COUNT(*) FROM teachers")
if cursor.fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO teachers VALUES (?,?,?,?)",
        [
            (1, "Иванов И.И.", "Математика", "1111"),
            (2, "Петров П.П.", "Информатика", "2222"),
        ]
    )
conn.commit()

# ================== STATE ==================
states = {}

def state(chat_id):
    return states.setdefault(chat_id, {"role": None, "step": None})

def reset_step(chat_id):
    states[chat_id]["step"] = None

# ================== UTILS ==================
def percent(grades):
    return round(sum(grades) / len(grades) / 5 * 100, 1)

def final_mark(p):
    if p <= 54: return 2
    if p <= 69: return 3
    if p <= 84: return 4
    return 5

# ================== MENUS ==================
def role_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_ADMIN, BTN_TEACHER, BTN_STUDENT)
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_ADD_TEACHER)
    kb.add(BTN_LIST_TEACHERS)
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
    kb.add(BTN_EXIT)
    return kb

# ================== START / EXIT ==================
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
    s["step"] = "admin_pin"
    bot.send_message(m.chat.id, "Введите PIN администратора:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "admin_pin")
def admin_auth(m):
    cursor.execute("SELECT id FROM admins WHERE pin=?", (m.text,))
    if not cursor.fetchone():
        bot.send_message(m.chat.id, "❌ Неверный PIN")
        return
    s = state(m.chat.id)
    s["role"] = "admin"
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "Меню администратора", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_ADD_TEACHER)
def add_teacher(m):
    s = state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "Доступ запрещён")
        return
    s["step"] = "add_teacher"
    bot.send_message(m.chat.id, "Введите: ФИО, Предмет")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "add_teacher")
def save_teacher(m):
    try:
        name, subject = map(str.strip, m.text.split(","))
    except ValueError:
        bot.send_message(m.chat.id, "Формат: ФИО, Предмет")
        return

    pin = str(random.randint(1000, 9999))
    cursor.execute(
        "INSERT INTO teachers VALUES (?,?,?,?)",
        (random.randint(100,999), name, subject, pin)
    )
    conn.commit()

    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ Преподаватель добавлен\n👤 {name}\n📘 {subject}\n🔐 PIN: {pin}",
        reply_markup=admin_menu()
    )

@bot.message_handler(func=lambda m: m.text == BTN_LIST_TEACHERS)
def list_teachers(m):
    cursor.execute("SELECT name, subject, pin FROM teachers")
    rows = cursor.fetchall()
    text = "📋 Преподаватели:\n\n"
    for n,s,p in rows:
        text += f"{n} — {s} — PIN: {p}\n"
    bot.send_message(m.chat.id, text, reply_markup=admin_menu())

# ================== TEACHER ==================
@bot.message_handler(func=lambda m: m.text == BTN_TEACHER)
def teacher_login(m):
    s = state(m.chat.id)
    s["step"] = "teacher_pin"
    bot.send_message(m.chat.id, "Введите PIN преподавателя:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "teacher_pin")
def teacher_auth(m):
    cursor.execute("SELECT name, subject FROM teachers WHERE pin=?", (m.text,))
    t = cursor.fetchone()
    if not t:
        bot.send_message(m.chat.id, "❌ Неверный PIN")
        return
    s = state(m.chat.id)
    s.update({"role":"teacher","name":t[0],"subject":t[1],"step":None})
    bot.send_message(m.chat.id, f"Предмет: {t[1]}", reply_markup=teacher_menu())

# ---- ADD STUDENT ----
@bot.message_handler(func=lambda m: m.text == BTN_ADD_STUDENT)
def add_student(m):
    s = state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "Только для преподавателя")
        return
    s["step"] = "add_student"
    bot.send_message(m.chat.id, "Введите ФИО ученика:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "add_student")
def save_student(m):
    pin = str(random.randint(1000,9999))
    cursor.execute(
        "INSERT INTO students VALUES (?,?,?)",
        (random.randint(100000,999999), m.text, pin)
    )
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ Ученик добавлен\n👤 {m.text}\n🔐 PIN: {pin}",
        reply_markup=teacher_menu()
    )

# ---- LIST STUDENTS ----
@bot.message_handler(func=lambda m: m.text == BTN_LIST_STUDENTS)
def list_students(m):
    s = state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "Только для преподавателя")
        return
    cursor.execute("SELECT name, pin FROM students")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "Учеников нет", reply_markup=teacher_menu())
        return
    text = "📋 Ученики:\n\n"
    for n,p in rows:
        text += f"{n} — PIN: {p}\n"
    bot.send_message(m.chat.id, text, reply_markup=teacher_menu())

# ---- ENTER GRADES ----
@bot.message_handler(func=lambda m: m.text == BTN_ENTER_GRADES)
def start_grades(m):
    s = state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "Только для преподавателя")
        return

    cursor.execute("SELECT name FROM students")
    students = cursor.fetchall()
    if not students:
        bot.send_message(m.chat.id, "Нет учеников", reply_markup=teacher_menu())
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for (name,) in students:
        kb.add(name)
    kb.add(BTN_EXIT)

    s["step"] = "choose_student"
    bot.send_message(m.chat.id, "Выберите ученика:", reply_markup=kb)

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "choose_student")
def choose_student(m):
    cursor.execute("SELECT id FROM students WHERE name=?", (m.text,))
    st = cursor.fetchone()
    if not st:
        bot.send_message(m.chat.id, "Выберите ученика из списка")
        return
    s = state(m.chat.id)
    s["student_id"] = st[0]
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
    bot.send_message(m.chat.id, "Введите оценки через запятую:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "grades")
def enter_grades(m):
    s = state(m.chat.id)
    s["grades"] = m.text.replace(" ","")
    s["step"] = "comment"
    bot.send_message(m.chat.id, "Комментарий к оценкам:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "comment")
def save_grades(m):
    s = state(m.chat.id)
    cursor.execute(
        "INSERT INTO grades VALUES (?,?,?,?,?)",
        (
            s["student_id"],
            s["subject"],
            s["semester"],
            s["grades"],
            m.text
        )
    )
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Оценки сохранены", reply_markup=teacher_menu())

# ================== STUDENT ==================
@bot.message_handler(func=lambda m: m.text == BTN_STUDENT)
def student_login(m):
    s = state(m.chat.id)
    s["step"] = "student_pin"
    bot.send_message(m.chat.id, "Введите PIN ученика:")

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "student_pin")
def student_auth(m):
    cursor.execute("SELECT id FROM students WHERE pin=?", (m.text,))
    st = cursor.fetchone()
    if not st:
        bot.send_message(m.chat.id, "❌ Неверный PIN")
        return
    s = state(m.chat.id)
    s.update({"role":"student","student_id":st[0],"step":None})
    bot.send_message(m.chat.id, "Меню ученика", reply_markup=student_menu())

@bot.message_handler(func=lambda m: m.text == BTN_PROGRESS)
def student_progress(m):
    s = state(m.chat.id)
    if s["role"] != "student":
        bot.send_message(m.chat.id, "Только для ученика")
        return

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
