# -*- coding: utf-8 -*-

import sqlite3
import asyncio
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
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))

TZ = ZoneInfo("Europe/Moscow")

WORK_DOW = {0,1,2,3,4,5}
WORK_START_HOUR = 10
WORK_END_HOUR = 18
SLOT_MINUTES = 30

MENU, CHOOSE_DATE, CHOOSE_TIME, ENTER_NAME, ENTER_PHONE = range(5)


def init_db():

    con = sqlite3.connect("appointments.db")
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        date TEXT,
        time TEXT,
        name TEXT,
        phone TEXT
    )
    """)

    con.commit()
    con.close()


def slot_taken(date,time):

    con = sqlite3.connect("appointments.db")
    cur = con.cursor()

    cur.execute(
        "SELECT 1 FROM appointments WHERE date=? AND time=?",
        (date,time)
    )

    r = cur.fetchone()
    con.close()

    return r is not None


def user_has_appointment(user_id):

    con = sqlite3.connect("appointments.db")
    cur = con.cursor()

    cur.execute(
        "SELECT date,time FROM appointments WHERE user_id=?",
        (user_id,)
    )

    r = cur.fetchone()
    con.close()

    return r


def save_appointment(user_id,username,date,time,name,phone):

    con = sqlite3.connect("appointments.db")
    cur = con.cursor()

    cur.execute("""
        INSERT INTO appointments(user_id,username,date,time,name,phone)
        VALUES(?,?,?,?,?,?)
    """,(user_id,username,date,time,name,phone))

    con.commit()
    con.close()


def generate_slots():

    slots = []

    start = dtime(WORK_START_HOUR,0)
    end = dtime(WORK_END_HOUR,0)

    step = timedelta(minutes=SLOT_MINUTES)

    cur = datetime.combine(datetime.today(),start)
    end_dt = datetime.combine(datetime.today(),end)

    while cur + step <= end_dt:

        slots.append(cur.strftime("%H:%M"))
        cur += step

    return slots


SLOTS = generate_slots()


def main_menu():

    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="book"),
            InlineKeyboardButton("2", callback_data="noop"),
            InlineKeyboardButton("3", callback_data="noop"),
            InlineKeyboardButton("4", callback_data="noop"),
            InlineKeyboardButton("5", callback_data="noop"),
            InlineKeyboardButton("6", callback_data="noop")
        ],
        [
            InlineKeyboardButton("❌ Отменить запись", callback_data="cancel")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def contact_keyboard():

    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Отправить контакт",request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def times_keyboard(date):

    kb = []

    for t in SLOTS:

        if slot_taken(date,t):
            kb.append([InlineKeyboardButton(f"⛔ {t}",callback_data="noop")])
        else:
            kb.append([InlineKeyboardButton(f"✅ {t}",callback_data=f"time:{t}")])

    return InlineKeyboardMarkup(kb)


async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    text = (
        "Инструкция записи\n\n"
        "1. Голосовая запись\n"
        "Отправьте голосовое сообщение.\n\n"
        "2. Тилди тандаңыз\n"
        "Выберите язык.\n\n"
        "3. Күндү белгилеңиз\n"
        "Выберите дату.\n\n"
        "4. Убакытты тандаңыз\n"
        "Выберите время.\n\n"
        "5. Атыңызды жазыңыз\n"
        "Напишите имя.\n\n"
        "6. Контакт жөнөтүү баскычын териңиз\n"
        "Нажмите кнопку отправить контакт.\n\n"
        "7. Поделитьсяны басыңыз\n"
        "Нажмите поделиться."
    )

    await update.message.reply_text(text, reply_markup=main_menu())
    return MENU


async def menu_click(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    if q.data == "cancel":

        con = sqlite3.connect("appointments.db")
        cur = con.cursor()

        cur.execute(
            "DELETE FROM appointments WHERE user_id=?",
            (q.from_user.id,)
        )

        con.commit()
        con.close()

        await q.edit_message_text("❌ Ваша запись отменена")
        return MENU


    if q.data == "book":

        existing = user_has_appointment(q.from_user.id)

        if existing:

            d,t = existing

            await q.edit_message_text(
                f"⚠️ У вас уже есть запись\n\n📅 {d}\n⏰ {t}"
            )

            return MENU


        today = datetime.now(TZ).date()

        kb = []

        for i in range(14):

            d = today + timedelta(days=i)

            if d.weekday() not in WORK_DOW:
                continue

            iso = d.isoformat()

            kb.append([
                InlineKeyboardButton(iso,callback_data=f"date:{iso}")
            ])

        await q.edit_message_text(
            "Выберите дату",
            reply_markup=InlineKeyboardMarkup(kb)
        )

        return CHOOSE_DATE


async def choose_date(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    date = q.data.split(":")[1]
    context.user_data["date"] = date

    await q.edit_message_text(
        "Выберите время",
        reply_markup=times_keyboard(date)
    )

    return CHOOSE_TIME


async def choose_time(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    t = q.data.split(":")[1]
    context.user_data["time"] = t

    await q.edit_message_text("Введите имя")
    return ENTER_NAME


async def enter_name(update:Update,context:ContextTypes.DEFAULT_TYPE):

    context.user_data["name"] = update.message.text

    await update.message.reply_text(
        "Отправьте контакт",
        reply_markup=contact_keyboard()
    )

    return ENTER_PHONE


async def enter_phone(update:Update,context:ContextTypes.DEFAULT_TYPE):

    phone = update.message.contact.phone_number

    context.user_data["phone"] = phone

    user = update.effective_user

    save_appointment(
        user.id,
        user.username or "",
        context.user_data["date"],
        context.user_data["time"],
        context.user_data["name"],
        phone
    )

    await update.message.reply_text(
        "✅ Запись подтверждена",
        reply_markup=ReplyKeyboardRemove()
    )

    await context.bot.send_message(
        ADMIN_USER_ID,
        f"🆕 Новая запись\n\n"
        f"📅 {context.user_data['date']} {context.user_data['time']}\n"
        f"👤 {context.user_data['name']}\n"
        f"📞 {phone}"
    )

    return MENU


async def reminder_loop(app):

    while True:

        now = datetime.now(TZ)

        con = sqlite3.connect("appointments.db")
        cur = con.cursor()

        cur.execute("SELECT user_id,date,time FROM appointments")
        rows = cur.fetchall()

        for user_id,date,time in rows:

            dt = datetime.fromisoformat(date+"T"+time)
            diff = dt - now

            if timedelta(hours=23,minutes=50) < diff < timedelta(hours=24,minutes=10):

                try:
                    await app.bot.send_message(
                        user_id,
                        f"🔔 Напоминание\n\n"
                        f"Завтра запись\n📅 {date}\n⏰ {time}"
                    )
                except:
                    pass

        con.close()
        await asyncio.sleep(600)


def main():

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(

        entry_points=[CommandHandler("start",start)],

        states={

            MENU:[CallbackQueryHandler(menu_click)],

            CHOOSE_DATE:[CallbackQueryHandler(choose_date)],

            CHOOSE_TIME:[CallbackQueryHandler(choose_time)],

            ENTER_NAME:[MessageHandler(filters.TEXT,enter_name)],

            ENTER_PHONE:[MessageHandler(filters.CONTACT,enter_phone)]

        },

        fallbacks=[CommandHandler("start",start)]

    )

    app.add_handler(conv)

    app.create_task(reminder_loop(app))

    print("Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()





































































































































































































































































