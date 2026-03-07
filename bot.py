# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
admin_user_id = os.getenv("ADMIN_USER_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")

if not admin_user_id:
    raise ValueError("ADMIN_USER_ID is not set")

ADMIN_USER_ID = int(admin_user_id)
TZ = ZoneInfo("Europe/Moscow")

WORK_DOW = {0, 1, 2, 3, 4, 5}
WORK_START_HOUR= 10
WORK_END_HOUR = 18
SLOT_MINUTES = 30

CHOOSE_LANG, MENU, CHOOSE_DATE, CHOOSE_TIME, ENTER_NAME, ENTER_PHONE, CONFIRM = range(7)

T = {
    "ru": {
        "hello": "Привет! Я бот записи на личный приём.\nВыбери действие:",
        "choose_lang": "Выбери язык / Тилди тандаңыз:",
        "menu": "Меню:",
        "book": "🗓 Записаться",
        "help": "❓ Помощь",
        "change_lang": "🌐 Сменить язык",
        "help_text": (
            "Как это работает:\n"
            "1) Выбираешь дату\n"
            "2) Выбираешь время\n"
            "3) Пишешь имя\n"
            "4) Отправляешь контакт кнопкой\n"
            "5) Подтверждаешь запись"
        ),
        "pick_date": "Выбери дату:",
        "pick_time": "Дата: {date}\nТеперь выбери время:",
        "enter_name": "Напиши, пожалуйста, твоё имя:",
        "enter_phone": "Теперь нажми кнопку ниже, чтобы отправить контакт:",
        "send_contact": "📱 Отправить контакт",
        "cancel_send": "❌ Отмена",
        "phone_not_received": "Пожалуйста, нажми кнопку «📱 Отправить контакт».",
        "review": (
            "Проверь запись:\n\n"
            "📅 Дата: {date}\n"
            "⏰ Время: {time}\n"
            "👤 Имя: {name}\n"
            "📞 Телефон: {phone}\n\n"
            "Подтвердить?"
        ),
        "confirm_yes": "✅ Подтвердить",
        "confirm_no": "❌ Отмена",
        "cancelled": "Ок, отменено. Возврат в меню:",
        "taken": "Упс, это время уже занято. Выбери другое:",
        "done": "✅ Запись подтверждена! Спасибо.\nЕсли нужно — напиши /start, чтобы записаться снова.",
        "back": "⬅️ Назад",
        "busy": "⛔ {t} занято",
        "free": "✅ {t}",
        "lang_set": "Язык установлен: Русский ✅",
        "choose_lang_from_menu": "Выбери новый язык:",
        "contact_only_own": "Пожалуйста, отправь свой контакт кнопкой ниже.",
    },
    "ky": {
        "hello": "Салам! Мен кезекке жазуучу ботмун.\nАракетти тандаңыз:",
        "choose_lang": "Тилди тандаңыз / Выбери язык:",
        "menu": "Меню:",
        "book": "🗓 Жазылуу",
        "help": "❓ Жардам",
        "change_lang": "🌐 Тилди өзгөртүү",
        "help_text": (
            "Бул кандай иштейт:\n"
            "1) Күндү тандайсыз\n"
            "2) Убакытты тандайсыз\n"
            "3) Атыңызды жазасыз\n"
            "4) Контактыңызды баскыч менен жөнөтөсүз\n"
            "5) Жазылууну ырастайсыз"
        ),
        "pick_date": "Күндү тандаңыз:",
        "pick_time": "Күн: {date}\nЭми убакытты тандаңыз:",
        "enter_name": "Атыңызды жазыңыз:",
        "enter_phone": "Эми төмөнкү баскычты басып, контактыңызды жөнөтүңүз:",
        "send_contact": "📱 Контакт жөнөтүү",
        "cancel_send": "❌ Жокко чыгаруу",
        "phone_not_received": "Сураныч, «📱 Контакт жөнөтүү» баскычын басыңыз.",
        "review": (
            "Жазылууну текшериңиз:\n\n"
            "📅 Күн: {date}\n"
            "⏰ Убакыт: {time}\n"
            "👤 Аты: {name}\n"
            "📞 Телефон: {phone}\n\n"
            "Ырастайсызбы?"
        ),
        "confirm_yes": "✅ Ырастоо",
        "confirm_no": "❌ Жокко чыгаруу",
        "cancelled": "Макул, жокко чыгарылды. Менюга кайтуу:",
        "taken": "Бул убакыт бош эмес. Башка убакыт тандаңыз:",
        "done": "✅ Жазылуу ырасталды! Рахмат.\nКайра жазылуу үчүн /start жазыңыз.",
        "back": "⬅️ Артка",
        "busy": "⛔ {t} бош эмес",
        "free": "✅ {t}",
        "lang_set": "Тил коюлду: Кыргызча ✅",
        "choose_lang_from_menu": "Жаңы тилди тандаңыз:",
        "contact_only_own": "Сураныч, төмөнкү баскыч менен өз контактыңызды жөнөтүңүз.",
    },
}

LANGS = [("Русский", "ru"), ("Кыргызча", "ky")]


def tr(context: ContextTypes.DEFAULT_TYPE, key: str) -> str:
    lang = context.user_data.get("lang", "ru")
    return T.get(lang, T["ru"]).get(key, T["ru"][key])


def init_db():
    con = sqlite3.connect("appointments.db")
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            date TEXT,
            time TEXT,
            name TEXT,
            phone TEXT,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT
        )
        """
    )

    con.commit()
    con.close()


def get_user_lang(user_id: int):
    con = sqlite3.connect("appointments.db")
    cur = con.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else None


def set_user_lang(user_id: int, lang: str):
    con = sqlite3.connect("appointments.db")
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO users (user_id, lang)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
        """,
        (user_id, lang),
    )
    con.commit()
    con.close()


def slot_taken(date_str: str, time_str: str) -> bool:
    con = sqlite3.connect("appointments.db")
    cur = con.cursor()
    cur.execute(
        "SELECT 1 FROM appointments WHERE date=? AND time=? LIMIT 1",
        (date_str, time_str),
    )
    row = cur.fetchone()
    con.close()
    return row is not None


def save_appointment(user_id, username, date_str, time_str, name, phone):
    con = sqlite3.connect("appointments.db")
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO appointments (user_id, username, date, time, name, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username,
            date_str,
            time_str,
            name,
            phone,
            datetime.now(TZ).isoformat(timespec="seconds"),
        ),
    )
    con.commit()
    con.close()


def lang_keyboard():
    kb = [[InlineKeyboardButton(title, callback_data=f"lang:{code}")] for title, code in LANGS]
    return InlineKeyboardMarkup(kb)


def main_menu(context):
    kb = [
        [InlineKeyboardButton(tr(context, "book"), callback_data="book")],
        [InlineKeyboardButton(tr(context, "help"), callback_data="help")],
        [InlineKeyboardButton(tr(context, "change_lang"), callback_data="change_lang")],
    ]
    return InlineKeyboardMarkup(kb)


def contact_keyboard(context):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(tr(context, "send_contact"), request_contact=True)],
            [KeyboardButton(tr(context, "cancel_send"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def format_date_for_user(context, iso_date):
    d = datetime.fromisoformat(iso_date).date()
    lang = context.user_data.get("lang", "ru")

    if lang == "ky":
        dow = ["Дш", "Шш", "Шр", "Бш", "Жм", "Иш", "Жк"][d.weekday()]
    else:
        dow = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][d.weekday()]

    return f"{dow} {d.day:02d}.{d.month:02d}"


def generate_slots():
    slots = []
    start = dtime(WORK_START_HOUR, 0)
    end = dtime(WORK_END_HOUR, 0)
    step = timedelta(minutes=SLOT_MINUTES)

    cur = datetime.combine(datetime.today().date(), start)
    end_dt = datetime.combine(datetime.today().date(), end)

    while cur + step <= end_dt:
        slots.append(cur.strftime("%H:%M"))
        cur += step

    return slots


SLOTS = generate_slots()


def times_keyboard(context, date_str):
    kb = []

    for t in SLOTS:
        if slot_taken(date_str, t):
            kb.append([InlineKeyboardButton(tr(context, "busy").format(t=t), callback_data="noop")])
        else:
            kb.append([InlineKeyboardButton(tr(context, "free").format(t=t), callback_data=f"time:{t}")])

    kb.append([InlineKeyboardButton(tr(context, "back"), callback_data="back:dates")])
    return InlineKeyboardMarkup(kb)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    saved = get_user_lang(user.id)

    context.user_data.clear()

    if saved:
        context.user_data["lang"] = saved
        await update.message.reply_text(tr(context, "hello"), reply_markup=main_menu(context))
        return MENU

    await update.message.reply_text(T["ru"]["choose_lang"], reply_markup=lang_keyboard())
    return CHOOSE_LANG


async def choose_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    lang = q.data.split(":")[1]
    context.user_data["lang"] = lang
    set_user_lang(q.from_user.id, lang)

    await q.edit_message_text(tr(context, "lang_set"))
    await q.message.reply_text(tr(context, "hello"), reply_markup=main_menu(context))
    return MENU


async def menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "book":
        today = datetime.now(TZ).date()
        kb = []
        for i in range(14):
            d = today + timedelta(days=i)
            if d.weekday() not in WORK_DOW:
                continue
            iso = d.isoformat()
            label = format_date_for_user(context, iso)
            kb.append([InlineKeyboardButton(label, callback_data=f"date:{iso}")])

        kb.append([InlineKeyboardButton(tr(context, "back"), callback_data="back:menu")])

        await q.edit_message_text(tr(context, "pick_date"), reply_markup=InlineKeyboardMarkup(kb))
        return CHOOSE_DATE

    if q.data == "help":
        await q.edit_message_text(tr(context, "help_text"), reply_markup=main_menu(context))
        return MENU

    if q.data == "change_lang":
        await q.edit_message_text(tr(context, "choose_lang_from_menu"), reply_markup=lang_keyboard())
        return CHOOSE_LANG

    return MENU


async def choose_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("date:"):
        date_str = q.data.split(":")[1]
        context.user_data["date"] = date_str

        pretty = format_date_for_user(context, date_str)

        await q.edit_message_text(
            tr(context, "pick_time").format(date=pretty),
            reply_markup=times_keyboard(context, date_str),
        )
        return CHOOSE_TIME

    return CHOOSE_DATE


async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("time:"):
        time_str = q.data.split(":")[1]
        context.user_data["time"] = time_str

        await q.edit_message_text(tr(context, "enter_name"))
        return ENTER_NAME

    return CHOOSE_TIME


async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text

    await update.message.reply_text(
        tr(context, "enter_phone"),
        reply_markup=contact_keyboard(context),
    )

    return ENTER_PHONE


async def enter_phone_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    context.user_data["phone"] = contact.phone_number

    date_str = context.user_data["date"]
    time_str = context.user_data["time"]

    text = tr(context, "review").format(
        date=format_date_for_user(context, date_str),
        time=time_str,
        name=context.user_data["name"],
        phone=context.user_data["phone"],
    )

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(context, "confirm_yes"), callback_data="confirm:yes")],
            [InlineKeyboardButton(tr(context, "confirm_no"), callback_data="confirm:no")],
        ]
    )

    await update.message.reply_text(text, reply_markup=kb)
    await update.message.reply_text(tr(context, "menu"), reply_markup=ReplyKeyboardRemove())

    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "confirm:no":
        await q.edit_message_text(tr(context, "cancelled"), reply_markup=main_menu(context))
        return MENU

    date_str = context.user_data["date"]
    time_str = context.user_data["time"]

    if slot_taken(date_str, time_str):
        await q.edit_message_text(tr(context, "taken"), reply_markup=times_keyboard(context, date_str))
        return CHOOSE_TIME

    user = q.from_user

    save_appointment(
        user.id,
        user.username or "",
        date_str,
        time_str,
        context.user_data["name"],
        context.user_data["phone"],
    )

    await q.edit_message_text(tr(context, "done"), reply_markup=main_menu(context))

    admin_msg = (
        "🆕 Новая запись:\n"
        f"📅 {date_str} {time_str}\n"
        f"👤 {context.user_data['name']}\n"
        f"📞 {context.user_data['phone']}"
    )

    await context.bot.send_message(ADMIN_USER_ID, admin_msg)

    return MENU


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_LANG: [CallbackQueryHandler(choose_lang, pattern="^lang:")],
            MENU: [CallbackQueryHandler(menu_click)],
            CHOOSE_DATE: [CallbackQueryHandler(choose_date)],
            CHOOSE_TIME: [CallbackQueryHandler(choose_time)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_PHONE: [MessageHandler(filters.CONTACT, enter_phone_contact)],
            CONFIRM: [CallbackQueryHandler(confirm)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()