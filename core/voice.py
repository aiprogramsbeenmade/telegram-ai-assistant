import os
import asyncio
from gtts import gTTS
from telegram import Bot


async def send_voice_message(bot_token: str, chat_id: int | str, text: str):
    """
    Converte un testo in audio (TTS) e lo invia come nota vocale nella chat Telegram.
    """
    if not text:
        return

    mp3_file = "voice_temp.mp3"

    try:
        # 1. Genera l'audio in italiano con gTTS
        tts = gTTS(text=text, lang='it')
        tts.save(mp3_file)

        # 2. Inizializza il Bot ed invia la nota vocale
        bot = Bot(token=bot_token)
        async with bot:
            with open(mp3_file, 'rb') as voice:
                await bot.send_voice(
                    chat_id=chat_id,
                    voice=voice,
                    caption="🎙️ *Notifica Vocale di Jarvis*",
                    parse_mode="Markdown"
                )
        print("✅ Nota vocale inviata con successo.")

    except Exception as e:
        print(f"⚠️ Errore durante l'invio del messaggio vocale: {e}")

    finally:
        # 3. Rimuove il file temporaneo
        if os.path.exists(mp3_file):
            os.remove(mp3_file)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Test rapido da riga di comando
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.getenv("MY_CHAT_ID", "")  # Il tuo ID numerico Telegram

    test_msg = "Ciao Matteo! Questo è un test. Jarvis ora può inviarti messaggi vocali direttamente in chat."
    asyncio.run(send_voice_message(TOKEN, CHAT_ID, test_msg))