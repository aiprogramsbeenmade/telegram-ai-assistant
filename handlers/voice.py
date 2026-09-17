import asyncio
import re
from telegram import Update
from telegram.ext import ContextTypes
from core.stt import transcribe_audio


def clean_whisper_text(raw_text: str) -> str:
    """Pulizia di sicurezza per eventuali timestamp o spazi residui."""
    cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\]', '', raw_text)
    return cleaned.strip()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🎙️ *Ascolto il vocale...*", parse_mode="Markdown")

    # Download dell'audio da Telegram
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    ogg_path = f"temp_{update.message.voice.file_id}.ogg"
    await voice_file.download_to_drive(ogg_path)

    # Trascrizione tramite Whisper (ora con modello ggml-small)
    raw_transcription = await asyncio.to_thread(transcribe_audio, ogg_path)
    transcribed_text = clean_whisper_text(raw_transcription) if raw_transcription else ""

    if not transcribed_text:
        await status_msg.edit_text("❌ Non sono riuscito a trascrivere il vocale.")
        return

    # Mostra la trascrizione pulita all'utente
    await status_msg.edit_text(f"🗣️ *Trascritto:* \"_{transcribed_text}_\"", parse_mode="Markdown")

    # Import locale ed esecuzione del router passando il testo pulito
    from main import route_message
    await route_message(update, context, user_text=transcribed_text)