import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOCTOR_CHAT_ID = os.getenv("DOCTOR_CHAT_ID")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
TZ = ZoneInfo("Asia/Tashkent")

LANG, NAME, PHONE, WEIGHT, HEIGHT, WAIST, MED, DOSE, SIDE = range(9)


def get_sheet(name, headers):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=scopes
    )

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SHEET_ID)

    try:
        sheet = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title=name,
            rows=2000,
            cols=len(headers)
        )
        sheet.append_row(headers)

    return sheet


def calculate_bmi(weight, height):
    height_m = float(height) / 100
    return round(float(weight) / (height_m * height_m), 1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    keyboard = [
        ["🇺🇿 O‘zbek"],
        ["🇷🇺 Русский"]
    ]

    await update.message.reply_text(
        "Assalomu alaykum!\n\n"
        "Ishonch Doctor Endokrinolog Botga xush kelibsiz.\n\n"
        "Tilni tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

    return LANG


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if "O‘zbek" in update.message.text:
        context.user_data["language"] = "uz"
        text = "Ismingizni kiriting:"
    else:
        context.user_data["language"] = "ru"
        text = "Введите ваше имя:"

    await update.message.reply_text(text)

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["name"] = update.message.text.strip()

    keyboard = [[
        KeyboardButton(
            "📱 Telefon raqamimni yuborish",
            request_contact=True
        )
    ]]

    await update.message.reply_text(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

    return PHONE


async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    context.user_data["phone"] = phone

    await update.message.reply_text(
        "Vazningizni kg da kiriting:"
    )

    return WEIGHT


async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        value = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Iltimos, vaznni raqam bilan kiriting. Masalan: 82.5"
        )
        return WEIGHT

    context.user_data["weight"] = value

    await update.message.reply_text(
        "Bo‘yingizni sm da kiriting:"
    )

    return HEIGHT


async def height(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        value = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Iltimos, bo‘yni raqam bilan kiriting. Masalan: 168"
        )
        return HEIGHT

    context.user_data["height"] = value

    await update.message.reply_text(
        "Bel aylanangizni sm da kiriting:"
    )

    return WAIST


async def waist(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        value = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Iltimos, bel aylanasini raqam bilan kiriting. Masalan: 96"
        )
        return WAIST

    context.user_data["waist"] = value

    keyboard = [
        ["Mounjaro", "Semavik"],
        ["Orsema", "Boshqa"]
    ]

    await update.message.reply_text(
        "Qaysi preparatni qabul qilyapsiz?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

    return MED


async def medication(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["medication"] = update.message.text.strip()

    await update.message.reply_text(
        "Preparat dozasini kiriting:"
    )

    return DOSE


async def dose(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["dose"] = update.message.text.strip()

    await update.message.reply_text(
        "Yon ta’sirlar bormi?\n\n"
        "Agar bo‘lmasa, «Yo‘q» deb yozing."
    )

    return SIDE


async def side_effect(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["side_effect"] = update.message.text.strip()

    data = context.user_data

    telegram_id = str(update.effective_user.id)

    date = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")

    bmi = calculate_bmi(
        data["weight"],
        data["height"]
    )

    patients = get_sheet(
        "Patients",
        [
            "ID",
            "Telegram_ID",
            "Ism",
            "Telefon",
            "Til",
            "Sana",
            "Vazn",
            "Bo‘y",
            "BMI",
            "Bel",
            "Preparat",
            "Doza",
            "Yon ta’sir"
        ]
    )

    monitoring = get_sheet(
        "Monitoring",
        [
            "ID",
            "Telegram_ID",
            "Sana",
            "Vazn",
            "Bo‘y",
            "BMI",
            "Bel",
            "Preparat",
            "Doza",
            "Yon ta’sir"
        ]
    )

    patients.append_row([
        telegram_id,
        telegram_id,
        data["name"],
        data["phone"],
        data["language"],
        date,
        data["weight"],
        data["height"],
        bmi,
        data["waist"],
        data["medication"],
        data["dose"],
        data["side_effect"]
    ])

    monitoring.append_row([
        telegram_id,
        telegram_id,
        date,
        data["weight"],
        data["height"],
        bmi,
        data["waist"],
        data["medication"],
        data["dose"],
        data["side_effect"]
    ])

    await update.message.reply_text(
        "✅ Ro‘yxatdan o‘tish yakunlandi!\n\n"
        f"👤 Ism: {data['name']}\n"
        f"⚖️ Vazn: {data['weight']} kg\n"
        f"📏 Bo‘y: {data['height']} sm\n"
        f"📊 BMI: {bmi}\n"
        f"📐 Bel: {data['waist']} sm\n"
        f"💊 Preparat: {data['medication']}\n"
        f"💉 Doza: {data['dose']}\n"
        f"⚠️ Yon ta’sir: {data['side_effect']}"
    )

    if (
        DOCTOR_CHAT_ID
        and data["side_effect"].lower()
        not in ["yo‘q", "yoq", "нет", "нету"]
    ):
        await context.bot.send_message(
            chat_id=DOCTOR_CHAT_ID,
            text=(
                "⚠️ BEMOR YON TA’SIR BILDIRDI!\n\n"
                f"👤 Bemor: {data['name']}\n"
                f"💊 Preparat: {data['medication']}\n"
                f"💉 Doza: {data['dose']}\n"
                f"⚠️ Yon ta’sir: {data['side_effect']}"
            )
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Ro‘yxatdan o‘tish bekor qilindi."
    )

    return ConversationHandler.END


def main():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    conversation = ConversationHandler(

        entry_points=[
            CommandHandler("start", start)
        ],

        states={

            LANG: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    language
                )
            ],

            NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    name
                )
            ],

            PHONE: [
                MessageHandler(
                    filters.CONTACT | (
                        filters.TEXT & ~filters.COMMAND
                    ),
                    phone
                )
            ],

            WEIGHT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    weight
                )
            ],

            HEIGHT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    height
                )
            ],

            WAIST: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    waist
                )
            ],

            MED: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    medication
                )
            ],

            DOSE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    dose
                )
            ],

            SIDE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    side_effect
                )
            ]
        },

        fallbacks=[
            CommandHandler("cancel", cancel)
        ]
    )

    application.add_handler(conversation)

    print("Ishonch Doctor Bot ishga tushdi!")

    application.run_polling()


if __name__ == "__main__":
    main()
