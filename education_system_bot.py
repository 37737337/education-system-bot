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
    raise RuntimeError("❌ BOT_TOKEN не найден в .env файле")

bot = telebot.TeleBot(BOT_TOKEN)

# ================== BUTTONS ==================
BTN_ADMIN = "🛠 Администратор"
BTN_TEACHER = "👨‍🏫 Преподаватель"
BTN_STUDENT = "👨‍🎓 Ученик"

BTN_ADD_STUDENT = "👤 Добавить ученика"
BTN_ENTER_GRADES = "✏️ Ввести оценки"
BTN_LIST_STUDENTS = "📋 Список учеников"
BTN_VIEW_STUDENT_GRADES = "🔍 Посмотреть оценки ученика"

BTN_ADD_TEACHER = "➕ Добавить преподавателя"
BTN_LIST_TEACHERS = "📋 Список преподавателей"
BTN_DELETE_PROFILE = "🗑 Удалить профиль"
BTN_BROADCAST = "📨 Рассылка"

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    chat_id INTEGER PRIMARY KEY
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

def get_state(chat_id):
    if chat_id not in states:
        states[chat_id] = {"role": None, "step": None}
    return states[chat_id]

def reset_step(chat_id):
    if chat_id in states:
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
    kb.add(BTN_BROADCAST)
    kb.add(BTN_DELETE_PROFILE)
    kb.add(BTN_EXIT)
    return kb

def teacher_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_ADD_STUDENT)
    kb.add(BTN_ENTER_GRADES, BTN_VIEW_STUDENT_GRADES)
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
    try:
        cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (m.chat.id,))
        conn.commit()
        s = get_state(m.chat.id)
        s["role"] = None
        s["step"] = None
        bot.send_message(
            m.chat.id,
            "🎓 <b>Добро пожаловать в SchoolBot!</b>\n\n"
            "Выберите свою роль:\n"
            "👨‍🎓 <b>Ученик</b> — просмотр оценок\n"
            "👨‍🏫 <b>Преподаватель</b> — ввод и управление\n"
            "🛠 <b>Администратор</b> — настройка системы",
            parse_mode="HTML",
            reply_markup=role_menu()
        )
    except Exception as e:
        print(f"⚠️ Ошибка в /start: {e}")
        bot.send_message(m.chat.id, "❌ Произошла ошибка. Попробуйте позже.")

@bot.message_handler(commands=["cancel"])
def cmd_cancel(m):
    cancel(m)

@bot.message_handler(func=lambda m: m.text == BTN_CANCEL)
def cancel(m):
    reset_step(m.chat.id)
    s = get_state(m.chat.id)
    if s["role"] == "admin":
        bot.send_message(m.chat.id, "↩️ Отменено. Вы в панели администратора.", reply_markup=admin_menu())
    elif s["role"] == "teacher":
        bot.send_message(m.chat.id, "↩️ Отменено. Вы в меню преподавателя.", reply_markup=teacher_menu())
    elif s["role"] == "student":
        bot.send_message(m.chat.id, "↩️ Отменено. Вы в личном кабинете.", reply_markup=student_menu())
    else:
        start(m)

@bot.message_handler(func=lambda m: m.text == BTN_EXIT)
def exit_menu(m):
    start(m)

# ================== ADMIN AUTH ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADMIN)
def admin_login(m):
    s = get_state(m.chat.id)
    s["role"] = None
    s["step"] = "admin_login"
    bot.send_message(m.chat.id, "🔐 Введите логин администратора:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "admin_login")
def admin_password(m):
    s = get_state(m.chat.id)
    s["login"] = m.text
    s["step"] = "admin_password"
    bot.send_message(m.chat.id, "🔑 Введите пароль:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "admin_password")
def admin_auth(m):
    try:
        s = get_state(m.chat.id)
        cursor.execute("SELECT id FROM admins WHERE login=? AND password=?", (s["login"], m.text))
        if not cursor.fetchone():
            bot.send_message(m.chat.id, "❌ Неверные данные. Попробуйте снова.", reply_markup=role_menu())
            reset_step(m.chat.id)
            return
        s["role"] = "admin"
        reset_step(m.chat.id)
        bot.send_message(
            m.chat.id,
            "✅ <b>Вы вошли как администратор!</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=admin_menu()
        )
    except Exception as e:
        print(f"⚠️ Ошибка в admin_auth: {e}")
        bot.send_message(m.chat.id, "❌ Внутренняя ошибка. Обратитесь к разработчику.")

# ================== ADD TEACHER (ADMIN) ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADD_TEACHER)
def add_teacher(m):
    s = get_state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "❌ Только для администраторов.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "teacher_name"
    bot.send_message(m.chat.id, "👤 Введите ФИО преподавателя (уникальное):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "teacher_name")
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
    s = get_state(m.chat.id)
    s["teacher_name"] = name
    s["step"] = "teacher_subject"
    bot.send_message(m.chat.id, "📚 Введите предмет:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "teacher_subject")
def save_teacher(m):
    subject = m.text.strip()
    if not subject:
        bot.send_message(m.chat.id, "❌ Предмет не может быть пустым.", reply_markup=cancel_button())
        return
    s = get_state(m.chat.id)
    name = s["teacher_name"]
    password = gen_password()
    cursor.execute("INSERT INTO teachers (login, subject, password) VALUES (?, ?, ?)", (name, subject, password))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ <b>Преподаватель добавлен!</b>\n"
        f"👤 ФИО: <b>{name}</b>\n"
        f"📚 Предмет: <b>{subject}</b>\n"
        f"🔑 Пароль: <code>{password}</code>\n\n"
        f"❗ Перешлите пароль — он не сохраняется!",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

# ================== LIST TEACHERS (ADMIN) ==================
@bot.message_handler(func=lambda m: m.text == BTN_LIST_TEACHERS)
def list_teachers(m):
    s = get_state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "❌ Только для администраторов.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    cursor.execute("SELECT login, subject FROM teachers")
    teachers = cursor.fetchall()
    if not teachers:
        bot.send_message(m.chat.id, "📭 Нет преподавателей.", reply_markup=admin_menu())
        return
    text = "📋 <b>Список преподавателей:</b>\n\n"
    for name, subject in teachers:
        text += f"• <b>{name}</b> — {subject}\n"
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=admin_menu())

# ================== BROADCAST (ADMIN) ==================
@bot.message_handler(func=lambda m: m.text == BTN_BROADCAST)
def broadcast_start(m):
    s = get_state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "❌ Только админ может делать рассылку.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "broadcast_text"
    bot.send_message(m.chat.id, "📬 Введите текст рассылки (можно с HTML):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "broadcast_text")
def broadcast_preview(m):
    s = get_state(m.chat.id)
    message_text = m.text.strip()
    if not message_text:
        bot.send_message(m.chat.id, "❌ Текст не может быть пустым.", reply_markup=cancel_button())
        return
    s["broadcast_content"] = message_text
    bot.send_message(m.chat.id, "📤 <b>Предпросмотр:</b>", parse_mode="HTML")
    try:
        bot.send_message(m.chat.id, message_text, parse_mode="HTML")
    except:
        bot.send_message(m.chat.id, "⚠️ Ошибка HTML. Отправляю как обычный текст.")
        bot.send_message(m.chat.id, message_text)
    s["step"] = "confirm_broadcast"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Отправить всем", "❌ Отменить")
    bot.send_message(m.chat.id, "❓ Отправить всем пользователям?", reply_markup=kb)

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "confirm_broadcast" and m.text == "✅ Отправить всем")
def broadcast_confirmed(m):
    s = get_state(m.chat.id)
    message_text = s["broadcast_content"]
    cursor.execute("SELECT chat_id FROM users")
    all_chats = cursor.fetchall()
    success = failed = 0
    for (chat_id,) in all_chats:
        try:
            bot.send_message(chat_id, message_text, parse_mode="HTML")
            success += 1
        except:
            failed += 1
    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ <b>Рассылка отправлена!</b>\n"
        f"👥 Получателей: {len(all_chats)}\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "confirm_broadcast" and m.text == "❌ Отменить")
def broadcast_cancelled(m):
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "📨 Рассылка отменена.", reply_markup=admin_menu())

# ================== DELETE PROFILE (ADMIN) ==================
@bot.message_handler(func=lambda m: m.text == BTN_DELETE_PROFILE)
def admin_delete(m):
    s = get_state(m.chat.id)
    if s["role"] != "admin":
        bot.send_message(m.chat.id, "❌ Только для администраторов.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "delete_login"
    bot.send_message(m.chat.id, "🗑 Введите ФИО для удаления:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "delete_login")
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
        bot.send_message(m.chat.id, "⚠️ Пользователь не найден.", reply_markup=admin_menu())
        reset_step(m.chat.id)
        return
    s = get_state(m.chat.id)
    s["delete_target"] = login
    s["step"] = "confirm_delete"
    bot.send_message(
        m.chat.id,
        f"❓ Удалить <b>{login}</b>?\n❗ Все данные будут потеряны!",
        parse_mode="HTML",
        reply_markup=confirm_delete_button()
    )

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "confirm_delete" and m.text == BTN_CONFIRM_DELETE)
def delete_confirmed(m):
    login = get_state(m.chat.id)["delete_target"]
    cursor.execute("DELETE FROM grades WHERE student_id IN (SELECT id FROM students WHERE login=?)", (login,))
    cursor.execute("DELETE FROM students WHERE login=?", (login,))
    cursor.execute("DELETE FROM teachers WHERE login=?", (login,))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, f"✅ Пользователь <b>{login}</b> удалён.", parse_mode="HTML", reply_markup=admin_menu())

# ================== TEACHER AUTH ==================
@bot.message_handler(func=lambda m: m.text == BTN_TEACHER)
def teacher_login(m):
    s = get_state(m.chat.id)
    s["role"] = None
    s["step"] = "teacher_login"
    bot.send_message(m.chat.id, "👤 Введите ваше ФИО:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "teacher_login")
def teacher_password(m):
    s = get_state(m.chat.id)
    s["login"] = m.text
    s["step"] = "teacher_password"
    bot.send_message(m.chat.id, "🔑 Введите пароль:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "teacher_password")
def teacher_auth(m):
    s = get_state(m.chat.id)
    cursor.execute("SELECT id, subject FROM teachers WHERE login=? AND password=?", (s["login"], m.text))
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Неверные данные.", reply_markup=role_menu())
        reset_step(m.chat.id)
        return
    s.update({"role": "teacher", "subject": row[1], "step": None})
    bot.send_message(
        m.chat.id,
        f"✅ <b>Добро пожаловать, {s['login']}!</b>\n"
        f"📚 Предмет: <b>{row[1]}</b>",
        parse_mode="HTML",
        reply_markup=teacher_menu()
    )

# ================== ADD STUDENT (TEACHER) ==================
@bot.message_handler(func=lambda m: m.text == BTN_ADD_STUDENT)
def add_student(m):
    s = get_state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "❌ Только для преподавателей.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "student_name"
    bot.send_message(m.chat.id, "👤 Введите ФИО ученика (уникальное):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "student_name")
def save_student(m):
    name = m.text.strip()
    if not name:
        bot.send_message(m.chat.id, "❌ ФИО не может быть пустым.", reply_markup=cancel_button())
        return
    cursor.execute("SELECT id FROM students WHERE login=?", (name,))
    if cursor.fetchone():
        bot.send_message(m.chat.id, "❌ Ученик уже существует!", reply_markup=teacher_menu())
        reset_step(m.chat.id)
        return
    password = gen_password()
    cursor.execute("INSERT INTO students (login, password) VALUES (?, ?)", (name, password))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"✅ <b>Ученик добавлен!</b>\n"
        f"👤 ФИО: <b>{name}</b>\n"
        f"🔑 Пароль: <code>{password}</code>",
        parse_mode="HTML",
        reply_markup=teacher_menu()
    )

# ================== LIST STUDENTS (TEACHER) ==================
@bot.message_handler(func=lambda m: m.text == BTN_LIST_STUDENTS)
def list_students(m):
    s = get_state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "❌ Только для преподавателей.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    cursor.execute("SELECT login FROM students")
    students = cursor.fetchall()
    if not students:
        bot.send_message(m.chat.id, "📭 Нет учеников.", reply_markup=teacher_menu())
        return
    text = "📋 <b>Список учеников:</b>\n\n"
    for (name,) in students:
        text += f"• {name}\n"
    text += "\n💡 Используйте «✏️ Ввести оценки» или «🔍 Посмотреть оценки»."
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=teacher_menu())

# ================== VIEW STUDENT GRADES (TEACHER) ==================
@bot.message_handler(func=lambda m: m.text == BTN_VIEW_STUDENT_GRADES)
def view_student_grades_start(m):
    s = get_state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "❌ Только для преподавателей.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    cursor.execute("SELECT login FROM students")
    students = cursor.fetchall()
    if not students:
        bot.send_message(m.chat.id, "📭 Нет учеников.", reply_markup=teacher_menu())
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for (name,) in students:
        kb.add(name)
    kb.add(BTN_CANCEL)
    s["step"] = "view_choose_student"
    bot.send_message(m.chat.id, "🔍 Выберите ученика:", reply_markup=kb)

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "view_choose_student")
def show_student_grades(m):
    student_name = m.text.strip()
    cursor.execute("SELECT id FROM students WHERE login=?", (student_name,))
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Ученик не найден.", reply_markup=cancel_button())
        return
    student_id = row[0]
    s = get_state(m.chat.id)
    cursor.execute("SELECT subject, semester, grades, comment FROM grades WHERE student_id=? AND subject=?", (student_id, s["subject"]))
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, f"📭 У <b>{student_name}</b> нет оценок по «{s['subject']}».", parse_mode="HTML", reply_markup=teacher_menu())
        reset_step(m.chat.id)
        return
    text = f"📊 <b>Оценки: {student_name}</b>\n\n"
    for subj, sem, g_str, comm in rows:
        grades = list(map(int, g_str.split(",")))
        p = percent(grades)
        text += (
            f"• <b>{subj}</b> — {sem} сем.\n"
            f"  Оценки: <code>{g_str}</code>\n"
            f"  Комментарий: {comm}\n"
            f"  Итог: <b>{final_mark(p)}</b>\n\n"
        )
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=teacher_menu())
    reset_step(m.chat.id)

# ================== ENTER GRADES (TEACHER) ==================
@bot.message_handler(func=lambda m: m.text == BTN_ENTER_GRADES)
def start_grades(m):
    s = get_state(m.chat.id)
    if s["role"] != "teacher":
        bot.send_message(m.chat.id, "❌ Только для преподавателей.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    cursor.execute("SELECT login FROM students")
    students = cursor.fetchall()
    if not students:
        bot.send_message(m.chat.id, "📭 Нет учеников.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for (name,) in students:
        kb.add(name)
    kb.add(BTN_CANCEL)
    s["step"] = "choose_student"
    bot.send_message(m.chat.id, "✏️ Выберите ученика:", reply_markup=kb)

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "choose_student")
def choose_student(m):
    cursor.execute("SELECT id FROM students WHERE login=?", (m.text.strip(),))
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Ученик не найден.", reply_markup=cancel_button())
        return
    s = get_state(m.chat.id)
    s["student_id"] = row[0]
    s["step"] = "semester"
    bot.send_message(m.chat.id, "🔢 Семестр (1 или 2):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "semester")
def enter_semester(m):
    if m.text not in ("1", "2"):
        bot.send_message(m.chat.id, "🔢 Введите 1 или 2.", reply_markup=cancel_button())
        return
    s = get_state(m.chat.id)
    s["semester"] = int(m.text)
    s["step"] = "grades"
    bot.send_message(m.chat.id, "🎯 Оценки через запятую (2–5):\nПример: <code>5,4,5</code>", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "grades")
def enter_grades(m):
    grades = validate_grades(m.text)
    if not grades:
        bot.send_message(m.chat.id, "❌ Оценки от 2 до 5 через запятую.", reply_markup=cancel_button())
        return
    s = get_state(m.chat.id)
    s["grades"] = ",".join(map(str, grades))
    s["step"] = "comment"
    bot.send_message(m.chat.id, "💬 Комментарий (можно пропустить):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "comment")
def save_grades(m):
    s = get_state(m.chat.id)
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
    s = get_state(m.chat.id)
    s["role"] = None
    s["step"] = "student_login"
    bot.send_message(m.chat.id, "👤 Введите ваше ФИО:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "student_login")
def student_password(m):
    s = get_state(m.chat.id)
    s["login"] = m.text
    s["step"] = "student_password"
    bot.send_message(m.chat.id, "🔑 Введите пароль:", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "student_password")
def student_auth(m):
    s = get_state(m.chat.id)
    cursor.execute("SELECT id FROM students WHERE login=? AND password=?", (s["login"], m.text))
    row = cursor.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ Неверные данные.", reply_markup=role_menu())
        reset_step(m.chat.id)
        return
    s.update({"role": "student", "student_id": row[0], "step": None})
    bot.send_message(m.chat.id, f"✅ Добро пожаловать, <b>{s['login']}</b>!", parse_mode="HTML", reply_markup=student_menu())

@bot.message_handler(func=lambda m: m.text == BTN_CHANGE_PASSWORD)
def change_password(m):
    s = get_state(m.chat.id)
    if s["role"] != "student":
        bot.send_message(m.chat.id, "❌ Только для учеников.", reply_markup=role_menu())
        return
    reset_step(m.chat.id)
    s["step"] = "new_password"
    bot.send_message(m.chat.id, "🔑 Новый пароль (минимум 6 символов):", reply_markup=cancel_button())

@bot.message_handler(func=lambda m: get_state(m.chat.id)["step"] == "new_password")
def save_new_password(m):
    new_pass = m.text.strip()
    if len(new_pass) < 6:
        bot.send_message(m.chat.id, "❌ Минимум 6 символов.", reply_markup=cancel_button())
        return
    s = get_state(m.chat.id)
    cursor.execute("UPDATE students SET password=? WHERE id=?", (new_pass, s["student_id"]))
    conn.commit()
    reset_step(m.chat.id)
    bot.send_message(m.chat.id, "✅ Пароль изменён!", reply_markup=student_menu())

@bot.message_handler(func=lambda m: m.text == BTN_PROGRESS)
def progress(m):
    s = get_state(m.chat.id)
    if s["role"] != "student":
        return
    reset_step(m.chat.id)
    cursor.execute("SELECT subject, semester, grades, comment FROM grades WHERE student_id=?", (s["student_id"],))
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "📭 У вас пока нет оценок.", reply_markup=student_menu())
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
            f"<b>{subj}</b> — {sem} сем.\n"
            f"Оценки: <code>{','.join(map(str, grades))}</code>\n"
            f"Комментарий: {comment_text}\n"
            f"Итог: <b>{final_mark(p)}</b>\n\n"
        )
    text += "🔽 Скопируйте, чтобы показать родителям."
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=student_menu())

# ================== RUN ==================
if __name__ == "__main__":
    print("🚀 SchoolBot запущен!")
    bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
