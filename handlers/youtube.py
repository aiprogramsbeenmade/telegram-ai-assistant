import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from telegram import Update
from telegram.ext import ContextTypes
import config
from core.llm import llm
from handlers.system import restricted


def extract_video_id(url: str) -> str | None:
    """Estrae l'ID del video dai vari formati di URL di YouTube."""
    pattern = r"(?:v=|\/([0-9A-Za-z_-]{11}).*|youtu\.be\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1) or match.group(2)
    return None


def get_clean_transcript(video_id: str) -> str | None:
    """Recupera la trascrizione istanziando l'API."""
    try:
        # Istanziamo la classe API
        yt_api = YouTubeTranscriptApi()

        # Chiamiamo .list() dall'istanza
        transcript_list = yt_api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(['it', 'en'])
        except Exception:
            transcript = transcript_list.find_generated_transcript(['it', 'en'])

        fetched_data = transcript.fetch()

        formatter = TextFormatter()
        return formatter.format_transcript(fetched_data)

    except Exception as e:
        print(f"Errore nel recupero della trascrizione: {e}")
        return None


@restricted
async def youtube_summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler di Telegram per elaborare i link YouTube."""
    message_text = update.message.text
    video_id = extract_video_id(message_text)

    if not video_id:
        await update.message.reply_text("Non sono riuscito a trovare un ID video valido nel link.")
        return

    status_msg = await update.message.reply_text("📥 Scaricando la trascrizione del video...")

    # Invocazione corretta con un solo argomento
    raw_transcript = get_clean_transcript(video_id)

    if not raw_transcript:
        await status_msg.edit_text(
            "❌ Non è stato possibile recuperare i sottotitoli per questo video (potrebbero essere disabilitati).")
        return

    await status_msg.edit_text("🧠 Trascrizione ottenuta! Sto elaborando il riassunto...")

    max_chars = 4000
    truncated_transcript = raw_transcript[:max_chars]

    prompt = (
        "<|im_start|>system\n"
        "Sei un assistente esperto nel sintetizzare contenuti. Riceverai la trascrizione di un video YouTube. "
        "Fornisci un riassunto conciso e ben strutturato in italiano, dividendo la risposta in:\n"
        "- **Concetto Principale**\n"
        "- **Punti Chiave** (massimo 5-6 punti essenziali)\n"
        "- **Conclusioni**<|im_end|>\n"
        f"<|im_start|>user\nEcco la trascrizione del video:\n\n{truncated_transcript}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    try:
        response = llm(
            prompt,
            max_tokens=768,
            temperature=0.7,
            stop=["<|im_end|>"]
        )
        summary = response["choices"][0]["text"].strip()

        await status_msg.edit_text(f"📝 **Riassunto Video YouTube:**\n\n{summary}", parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text("⚠️ Si è verificato un errore durante la generazione del riassunto.")