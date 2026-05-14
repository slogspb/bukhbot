import os
import re
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from sheets import append_invoice_row
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ALLOWED_USER = os.getenv("ALLOWED_USER", "recrutmaster")
PAYMENT_FORECAST_DAYS = {"маркет.операции": 30}

def parse_contractor(text):
    match = re.search(r"сч[её]т\s+(.+?)(?:\s+#|\s*\n|$)", text, re.IGNORECASE | re.UNICODE)
    return match.group(1).strip() if match else ""

def parse_period(text):
    match = re.search(r"(\d{1,2})\s*[-–]\s*(\d{1,2}[./]\d{2})", text)
    return f"{match.group(1)}-{match.group(2)}" if match else ""

def parse_period_end_date(text, msg_date):
    match = re.search(r"\d{1,2}\s*[-–]\s*(\d{1,2})[./](\d{2})", text)
    if not match:
        return None
    try:
        return datetime(msg_date.year, int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None

def parse_amounts(text):
    cleaned = re.sub(r"(\d)\s+(\d)", r"\1\2", text)
    match = re.search(r"(\d+)\s*\(с\s*ндс\s*(\d+)\)", cleaned, re.IGNORECASE)
    if match:
        bez = match.group(1)
        s = match.group(2)
        return bez, str(int(s) - int(bez)), s
    return "", "", ""

def forecast_date(contractor, period_end, msg_date):
    base = period_end if period_end else msg_date
    for key, days in PAYMENT_FORECAST_DAYS.items():
        if key in contractor.lower():
            return (base + timedelta(days=days)).strftime("%d.%m.%Y")
    return ""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.channel_post
    if not message or not message.text:
        return
    sender = message.from_user
    if not sender or (sender.username or "").lower() != ALLOWED_USER.lower():
        return
    text = message.text
    if not re.search(r"сч[её]т", text, re.IGNORECASE):
        return
    msg_date = message.date
    contractor = parse_contractor(text)
    period_end = parse_period_end_date(text, msg_date)
    bez_nds, nds_val, s_nds = parse_amounts(text)
    if not contractor or not s_nds:
        logger.warning(f"Не распознано:\n{text[:200]}")
        return
    row = {
        "date": msg_date.strftime("%d.%m.%Y"),
        "forecast": forecast_date(contractor, period_end, msg_date),
        "contractor": contractor,
        "s_nds": s_nds,
        "nds": nds_val,
        "bez_nds": bez_nds,
        "period": parse_period(text),
    }
    logger.info(f"Распознано: {contractor} | {bez_nds} / {s_nds}")
    try:
        append_invoice_row(row)
        logger.info("Записано в таблицу")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(
        filters.TEXT & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        handle_message
    ))
    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
