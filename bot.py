import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from datetime import datetime
import pytz

from excel_utils import append_transaction, read_transactions
from openai_parser import parse_with_openai

# Configuración
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
lima_tz = pytz.timezone("America/Lima")

logging.basicConfig(level=logging.INFO)

# Función para procesar mensajes
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    if not user_text:
        await update.message.reply_text("Por favor ingresa un texto válido.")
        return

    parsed = parse_with_openai(user_text)
    if parsed and parsed.get("amount"):
        fecha_registro = datetime.now(lima_tz).strftime("%Y-%m-%d %H:%M:%S")
        append_transaction(
            parsed["date"],
            parsed["category"],
            parsed["subcategory"],
            parsed["amount"],
            user_text,
            fecha_registro
        )
        await update.message.reply_text(
            f"✅ Movimiento registrado:\n"
            f"- Fecha: {parsed['date']}\n"
            f"- Categoría: {parsed['category']} / {parsed['subcategory']}\n"
            f"- Monto: {parsed['amount']} {parsed.get('currency', '')}\n"
            f"- Comentario: {parsed['description']}"
        )
    else:
        await update.message.reply_text("❌ No pude interpretar tu mensaje.")

# Inicializar bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
