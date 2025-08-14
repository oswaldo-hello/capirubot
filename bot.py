import os
import logging
import tempfile  # NUEVO
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from datetime import datetime
import pytz
from openai import OpenAI  # NUEVO

# Configuración Json
json_content = os.environ.get("GOOGLE_SHEET_CREDENTIALS_JSON")
if json_content:
    with open("credentials.json", "w") as f:
        f.write(json_content)

from excel_utils import append_transaction, read_transactions
from openai_parser import parse_with_openai

# Configuración
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # NUEVO
client = OpenAI(api_key=OPENAI_API_KEY)       # NUEVO
lima_tz = pytz.timezone("America/Lima")

logging.basicConfig(level=logging.INFO)

# Función para procesar mensajes (texto o transcripción)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text_override=None):
    user_text = user_text_override or update.message.text.strip()
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

# NUEVO: Manejar mensajes de voz/audio
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice_or_audio = update.message.voice or update.message.audio
    if not voice_or_audio:
        await update.message.reply_text("No pude recibir el audio.")
        return

    # Guardar archivo en /tmp
    with tempfile.NamedTemporaryFile(dir="/tmp", suffix=".ogg", delete=False) as tmp_file:
        file_path = tmp_file.name
    tg_file = await context.bot.get_file(voice_or_audio.file_id)
    await tg_file.download_to_drive(file_path)

    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",  # Modelo rápido de OpenAI
                file=audio_file
            )
        transcribed_text = transcript.text.strip()
    except Exception as e:
        await update.message.reply_text(f"❌ Error al transcribir el audio: {e}")
        return
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)  # Limpieza

    # Reusar el flujo de texto
    await handle_message(update, context, user_text_override=transcribed_text)

# Inicializar bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handler para texto
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Handler para voz/audio
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))  # NUEVO

    app.run_polling()

if __name__ == "__main__":
    main()
