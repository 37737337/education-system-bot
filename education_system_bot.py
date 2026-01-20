import os
import sqlite3
import random
import string
import time
import telebot
from telebot import types
from dotenv import load_dotenv

# ================== CONFIG ==================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в .env файле")

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
BTN_CANCEL = "❌ Отмена"
BTN_CONFIRM_DELETE = "✅ Подтвердить удаление"

# ================== DATABASE ==================
conn = sqlite3.connect("school.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY,
    login TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY,
    login TEXT UNIQUE,
    subject TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY,
    login TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS grades(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    subject TEXT,
    semester INTEGER,
    grades TEXT,
    comment TEXT,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
)
""")
conn.commit()

# ================== SEED DEFAULT ADMIN ==================
cursor.execute("SELECT COUNT(*) FROM admins")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO admins (login, password) VALUES ('admin', 'admin123')")
    conn.commit()

# ================== STATE MANAGEMENT ==================
states = {}

def state(chat_id):
    return states.setdefault(chat_id, {"role": None, "step": None})

def reset_step(chat_id):
    states[chat_id]["step"] = None

# ================== UTILS ==================
def gen_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def percent(grades):
    if not grades:
        return 0.0
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

# ================== KEYBOARDS ==================
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

def cancel_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_CANCEL)
    return kb

def confirm_delete_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_CONFIRM_DELETE, BTN_CANCEL)
    return kb

# ================== START & EXIT ==================
@bot.message_handler(commands=["start"])
def start(m):
    s = state(m.chat.id)
    s["role"] = None
    s["step"] = None
    bot.send_message(m.chat.id, "👋 Добро пожаловать!\nВыберите роль:", reply_markup=role_menu())

@bot.message_handler(func=lambda m: m.text == BTN_CANCEL)
def cancel(m):
    reset_step(m.chat.id)
    s = state(m.chat.id)
    if s["role"] == "admin":
        bot.send_message(m.chat.id, "↩️ Отменено.", reply_markup=admin_menu())
    elif s["role"] == "teacher":
        bot.send_message(m.chat.id, "↩️ Отменено.", reply_markup=teacher_menu())
    elif s["role"] == "student":
        bot.send_message(m.chat.id, "↩️ Отменено.", reply_markup=student_menu())
    else:
        start(m)

@bot.message_handler(func=lambda m: m.text == BTN_EXIT)
def exit_menu(m):
    start(m)

# ================== ADMIN AUTH ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADMIN)
def admin_login(m):
    s = state(m.chat.id)
    s["role"] = None
    s["step"] = "admin_login"
    bot.send_message(m.chat.id, "🔐 Введите логин администратора:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "admin_login")
def admin_password(m):
    s = state(m.chat.id)
    s["login"] = m.text
    s["step"] = "admin_password"
    bot.send_message(m.chat.id, "🔑 Введите пароль:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "admin_password")
def admin_auth(m):
    s = state(m.chat.id)
    cursor.execute("SELECT id FROM admins WHERE login=? AND password=?", (s["login"], m.text))
    if not cursor.fetchone():
        bot.send_message(m.chat.id, "❌ Неверные данные", reply_markup=role_menu())
        reset_step(m.chat.id)
        return
    s["role"] = "admin"
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Вы вошли как администратор", reply_markup=admin_menu())

# ================== ADD TEACHER (ADMIN) ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADD_TEACHER)
def add_teacher(m):
    s = state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "❌ Эта функция доступна только администратору.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)  # ← КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ
    s["step"] = "teacher_name"
    bot.send_message(m.chat.id, "👤 Введите ФИО преподавателя (должно быть уникальным):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "teacher_name")
def teacher_enter_subject(m):
    name = m.text.strip()
    if not name:
        bot.send_message(m.chat.id, "❌ ФИО не может быть пустым.", reply_markup=cancel_button())
        return
    cursor.execute("SELECT id FROM teachers WHERE login=?", (name,))
    if cursor.fetchone():
        bot.send_message(m.chat.id, "❌ Преподаватель с таким ФИО уже существует!", reply_markup=admin_menu())
        reset_step(m.chat.id)
        return
    s = state(m.chat.id)
    s["teacher_name"] = name
    s["step"] = "teacher_subject"
    bot.send_message(m.chat.id, "📚 Введите предмет, который ведёт преподаватель:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "teacher_subject")
def save_teacher(m):
    subject = m.text.strip()
    if not subject:
        bot.send_message(m.chat.id, "❌ Предмет не может быть пустым.", reply_markup=cancel_button())
        return
    s = state(m.chat.id)
    name = s["teacher_name"]
    password = gen_password()
    cursor.execute("INSERT INTO teachers (login, subject, password) VALUES (?, ?, ?)", (name, subject, password))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ Преподаватель успешно добавлен!\n\n"
        f"ФИО: <b>{name}</b>\n"
        f"Предмет: <b>{subject}</b>\n"
        f"Пароль: <code>{password}</code>\n\n"
        f"⚠️ Перешлите пароль преподавателю!",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

# ================== LIST TEACHERS (ADMIN) ==================
@bot.message_handler(func=lambda m: m.text == BTN_LIST_TEACHERS)
def list_teachers(m):
    s = state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "❌ Эта функция доступна только администратору.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)  # ← КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ
    cursor.execute("SELECT login, subject FROM teachers")
    teachers = cursor.fetchall()
    if not teachers:
        bot.send_message(m.chat.id, "📭 Нет преподавателей в системе.", reply_markup=admin_menu())
        return
    text = "📋 <b>Список преподавателей:</b>\n\n"
    for name, subject in teachers:
        text += f"• <b>{name}</b> — {subject}\n"
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=admin_menu())

# ================== DELETE PROFILE (ADMIN) ==================
@bot.message_handler(func=lambda m: m.text == BTN_DELETE_PROFILE)
def admin_delete(m):
    s = state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "❌ Эта функция доступна только администратору.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "delete_login"
    bot.send_message(m.chat.id, "🗑 Введите ФИО пользователя для удаления:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "delete_login")
def admin_delete_confirm(m):
    login = m.text.strip()
    if not login:
        bot.send_message(m.chat.id, "❌ ФИО не может быть пустым.", reply_markup=cancel_button())
        return
    exists = False
    cursor.execute("SELECT 1 FROM students WHERE login=?", (login,))
    if cursor.fetchone():
        exists = True
    else:
        cursor.execute("SELECT 1 FROM teachers WHERE login=?", (login,))
        if cursor.fetchone():
            exists = True
    if not exists:
        bot.send_message(m.chat.id, "⚠️ Пользователь с таким ФИО не найден.", reply_markup=admin_menu())
        reset_step(m.chat.id)
        return
    s = state(m.chat.id)
    s["delete_target"] = login
    s["step"] = "confirm_delete"
    bot.send_message(
        m.chat.id,
        f"❓ Вы уверены, что хотите удалить <b>{login}</b>?\n"
        f"Все данные будут удалены безвозвратно!",
        parse_mode="HTML",
        reply_markup=confirm_delete_button()
    )

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "confirm_delete" and m.text == BTN_CONFIRM_DELETE)
def delete_confirmed(m):
    login = state(m.chat.id)["delete_target"]
    cursor.execute("DELETE FROM grades WHERE student_id IN (SELECT id FROM students WHERE login=?)", (login,))
    cursor.execute("DELETE FROM students WHERE login=?", (login,))
    cursor.execute("DELETE FROM teachers WHERE login=?", (login,))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, f"✅ Пользователь <b>{login}</b> удалён.", parse_mode="HTML", reply_markup=admin_menu())

# ================== TEACHER AUTH ==================
@bot.message_handler(func=lambda m: m.text == BTN_TEACHER)
def teacher_login(m):
    s = state(m.chat.id)
    s["role"] = None
    s["step"] = "teacher_login"
    bot.send_message(m.chat.id, "👤 Введите ваше ФИО:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "teacher_login")
def teacher_password(m):
    s = state(m.chat.id)
    s["login"] = m.text
    s["step"] = "teacher_password"
    bot.send_message(m.chat.id, "🔑 Введите пароль:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "teacher_password")
def teacher_auth(m):
    s = state(m.chat.id)
    cursor.execute("SELECT id, subject FROM teachers WHERE login=? AND password=?", (s["login"], m.text))
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Неверные данные", reply_markup=role_menu())
        reset_step(m.chat.id)
        return
    s.update({"role": "teacher", "subject": row[1], "step": None})
    bot.send_message(m.chat.id, f"✅ Добро пожаловать!\nПредмет: <b>{row[1]}</b>", parse_mode="HTML", reply_markup=teacher_menu())

# ================== ADD STUDENT (TEACHER) ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADD_STUDENT)
def add_student(m):
    s = state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "❌ Эта функция доступна только преподавателю.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "student_name"
    bot.send_message(m.chat.id, "👤 Введите ФИО ученика (уникальное):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "student_name")
def save_student(m):
    name = m.text.strip()
    if not name:
        bot.send_message(m.chat.id, "❌ ФИО не может быть пустым.", reply_markup=cancel_button())
        return
    cursor.execute("SELECT id FROM students WHERE login=?", (name,))
    if cursor.fetchone():
        bot.send_message(m.chat.id, "❌ Ученик с таким ФИО уже существует!", reply_markup=teacher_menu())
        reset_step(m.chat.id)
        return
    password = gen_password()
    cursor.execute("INSERT INTO students (login, password) VALUES (?, ?)", (name, password))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ Ученик добавлен!\n\nЛогин: <b>{name}</b>\nПароль: <code>{password}</code>",
        parse_mode="HTML",
        reply_markup=teacher_menu()
    )

# ================== ENTER GRADES (TEACHER) ==================
@bot.message_handler(func=lambda m: m.text == BTN_ENTER_GRADES)
def start_grades(m):
    s = state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "❌ Эта функция доступна только преподавателю.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    cursor.execute("SELECT login FROM students")
    students = cursor.fetchall()
    if not students:
        bot.send_message(m.chat.id, "📭 Нет учеников в системе.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for (name,) in students:
        kb.add(name)
    kb.add(BTN_CANCEL)
    s["step"] = "choose_student"
    bot.send_message(m.chat.id, "Выберите ученика:", reply_markup=kb)

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "choose_student")
def choose_student(m):
    cursor.execute("SELECT id FROM students WHERE login=?", (m.text.strip(),))
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Ученик не найден.", reply_markup=cancel_button())
        return
    s = state(m.chat.id)
    s["student_id"] = row[0]
    s["step"] = "semester"
    bot.send_message(m.chat.id, "Введите семестр (1 или 2):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "semester")
def enter_semester(m):
    if m.text not in ("1", "2"):
        bot.send_message(m.chat.id, "🔢 Введите 1 или 2", reply_markup=cancel_button())
        return
    s = state(m.chat.id)
    s["semester"] = int(m.text)
    s["step"] = "grades"
    bot.send_message(m.chat.id, "Введите оценки (2–5) через запятую:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "grades")
def enter_grades(m):
    grades = validate_grades(m.text)
    if not grades:
        bot.send_message(m.chat.id, "❌ Оценки должны быть от 2 до 5, через запятую.", reply_markup=cancel_button())
        return
    s = state(m.chat.id)
    s["grades"] = ",".join(map(str, grades))
    s["step"] = "comment"
    bot.send_message(m.chat.id, "Комментарий (можно оставить пустым):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "comment")
def save_grades(m):
    s = state(m.chat.id)
    comment = m.text.strip() or "—"
    cursor.execute(
        "INSERT INTO grades (student_id, subject, semester, grades, comment) VALUES (?,?,?,?,?)",
        (s["student_id"], s["subject"], s["semester"], s["grades"], comment)
    )
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Оценки сохранены!", reply_markup=teacher_menu())

# ================== STUDENT AUTH ==================
@bot.message_handler(func=lambda m: m.text == BTN_STUDENT)
def student_login(m):
    s = state(m.chat.id)
    s["role"] = None
    s["step"] = "student_login"
    bot.send_message(m.chat.id, "👤 Введите ваше ФИО:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "student_login")
def student_password(m):
    s = state(m.chat.id)
    s["login"] = m.text
    s["step"] = "student_password"
    bot.send_message(m.chat.id, "🔑 Введите пароль:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "student_password")
def student_auth(m):
    s = state(m.chat.id)
    cursor.execute("SELECT id FROM students WHERE login=? AND password=?", (s["login"], m.text))
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Неверные данные", reply_markup=role_menu())
        reset_step(m.chat.id)
        return
    s.update({"role": "student", "student_id": row[0], "step": None})
    bot.send_message(m.chat.id, "✅ Добро пожаловать в личный кабинет!", reply_markup=student_menu())

@bot.message_handler(func=lambda m: m.text == BTN_CHANGE_PASSWORD)
def change_password(m):
    s = state(m.chat.id)
    if s["role"] != "student":
        bot.send_message(m.chat.id, "❌ Эта функция доступна только ученику.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "new_password"
    bot.send_message(m.chat.id, "🔑 Введите новый пароль (минимум 6 символов):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: state(m.chat.id)["step"] == "new_password")
def save_new_password(m):
    new_pass = m.text.strip()
    if len(new_pass) < 6:
        bot.send_message(m.chat.id, "❌ Пароль должен быть не короче 6 символов.", reply_markup=cancel_button())
        return
    s = state(m.chat.id)
    cursor.execute("UPDATE students SET password=? WHERE id=?", (new_pass, s["student_id"]))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Пароль изменён!", reply_markup=student_menu())

@bot.message_handler(func=lambda m: m.text == BTN_PROGRESS)
def progress(m):
    s = state(m.chat.id)
    if s["role"] != "student":
        return
    reset_step(m.chat.id)
    cursor.execute("SELECT subject, semester, grades, comment FROM grades WHERE student_id=?", (s["student_id"],))
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "📭 У вас пока нет оценок.")
        return
    data = {}
    comments = {}
    for subj, sem, g, c in rows:
        key = (subj, sem)
        data.setdefault(key, []).extend(map(int, g.split(",")))
        comments.setdefault(key, []).append(c)
    text = "📊 <b>Ваша успеваемость:</b>\n\n"
    for (subj, sem), grades in data.items():
        p = percent(grades)
        comment_text = "; ".join(filter(lambda x: x != "—", comments[(subj, sem)])) or "—"
        text += (
            f"<b>{subj}</b> — {sem} семестр\n"
            f"Оценки: {','.join(map(str, grades))}\n"
            f"Комментарий: {comment_text}\n"
            f"Процент: {p}% → Итог: <b>{final_mark(p)}</b>\n\n"
        )
    bot.send_message(m.chat.id, text, parse_mode="HTML")

# ================== RUN ==================
if __name__ == "__main__":
    print("🚀 Бот запущен...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
