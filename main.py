import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
from database import db_manager
from core.router import parse_intents
from handlers import chat, progress, reminders, emails, system, voice, weather, maps, search
from handlers.youtube import youtube_summary_handler
from handlers.emails import handle_email_callback, handle
from handlers.contacts import show_rubrica, add_contact, handle_contact_callback
from core.voice import send_voice_message
from core.system_status import get_system_status
from handlers.pdf_handler import extract_text_from_pdf

import os
from functools import wraps
from dotenv import load_dotenv
import asyncio

logging.basicConfig(level=logging.INFO)

load_dotenv()

ALLOWED_USER_ID = int(os.getenv("ALLOWED_TELEGRAM_USER_ID", "0"))

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def pdf_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Intercetta i file PDF inviati dall'utente, estrae il testo e lo salva nel contesto sessione.
    """
    document = update.message.document

    if not document.file_name.lower().endswith('.pdf'):
        return

    await update.message.reply_text("📄 *Ricevuto file PDF. Analisi ed estrazione del testo in corso...*",
                                    parse_mode="Markdown")

    # 1. Scarica il file dal server Telegram
    file = await context.bot.get_file(document.file_id)
    file_path = os.path.join(DOWNLOAD_DIR, document.file_name)
    await file.download_to_drive(file_path)

    try:
        # 2. Estrae il testo tramite pypdf
        pdf_data = extract_text_from_pdf(file_path)

        if "error" in pdf_data:
            await update.message.reply_text(f"❌ Errore: {pdf_data['error']}")
            return

        # 3. Salva i dati del PDF nella memoria di sessione dell'utente (user_data)
        context.user_data["active_pdf"] = {
            "filename": document.file_name,
            "data": pdf_data
        }

        pages_read = pdf_data["pages_read"]
        total_pages = pdf_data["total_pages"]

        caption = (
            f"✅ *PDF caricato con successo!*\n\n"
            f"📌 *Nome:* `{document.file_name}`\n"
            f"📖 *Pagine analizzate:* `{pages_read}/{total_pages}`\n\n"
            f"Ora puoi farmi qualsiasi domanda sul contenuto di questo documento!\n"
            f"_(Usa /closepdf per chiudere la sessione sul PDF)_"
        )
        await update.message.reply_text(caption, parse_mode="Markdown")

    finally:
        # Pulizia del file locale scaricato per mantenere pulito il server
        if os.path.exists(file_path):
            os.remove(file_path)


def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None

        if user_id != ALLOWED_USER_ID:
            print(f"⚠️ Tentativo di accesso non autorizzato da ID: {user_id}")
            if update.message:
                await update.message.reply_text("⛔ Non sei autorizzato ad utilizzare questo bot.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Non autorizzato.", show_alert=True)
            return

        return await func(update, context, *args, **kwargs)

    return wrapped


async def is_authorized(update: Update) -> bool:
    """Verifica se il mittente del messaggio è l'utente autorizzato."""
    user = update.effective_user
    if user and user.id == ALLOWED_USER_ID:
        return True

    if update.message:
        await update.message.reply_text("⛔ Accesso non autorizzato.")
    return False


async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str = None):
    if not await is_authorized(update):
        return

    text = user_text or (update.message.text if update.message else "")
    if not text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("🤔 *Sto pensando...*", parse_mode="Markdown")
    context.user_data["status_msg"] = status_msg

    # 1. Stato di attesa input (es. nome contatto per la rubrica)
    if context.user_data.get("awaiting_contact_name"):
        await emails.handle(update, context, user_text=text, status_msg=status_msg)
        return

    # 2. Parsing multi-intent tramite LLM
    actions = parse_intents(text)

    # 3. Esecuzione sequenziale delle azioni estratte
    for action in actions:
        intent = action.get("intent", "chat")
        sub_query = action.get("query", text)

        if intent == "email":
            await emails.handle(update, context, user_text=sub_query)
        elif intent == "weather":
            await weather.handle(update, context, user_text=sub_query)
        elif intent == "maps":
            await maps.handle_route(update, context, user_text=sub_query)
        elif intent == "reminder":
            await reminders.handle(update, context, user_text=sub_query)
        elif intent == "progress":
            await progress.handle(update, context, user_text=sub_query)
        elif intent in ["chat", "pdf_qa"]:
            await chat.handle(update, context, user_text=sub_query)


def restore_pending_jobs(scheduler, app):
    pending = db_manager.get_pending_reminders()
    now = datetime.now()
    for rem in pending:
        rem_id, chat_id, testo, data_ora_str = rem
        target_dt = datetime.strptime(data_ora_str, "%Y-%m-%d %H:%M:%S")
        if target_dt > now:
            scheduler.add_job(
                reminders.send_reminder_notification,
                'date',
                run_date=target_dt,
                args=[app, chat_id, testo, rem_id],
                id=f"rem_{rem_id}"
            )


async def post_init(app):
    scheduler = AsyncIOScheduler()
    scheduler.start()
    app.bot_data["scheduler"] = scheduler

    restore_pending_jobs(scheduler, app)
    print("Scheduler avviato con successo nell'event loop!")


async def voice_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Legge il messaggio a cui l'utente sta rispondendo e lo converte in nota vocale.
    """
    message = update.message

    if not message.reply_to_message:
        await message.reply_text(
            "⚠️ Rispondi a un messaggio di testo con il comando /vocal o /voice per farlo leggere a Jarvis!"
        )
        return

    target_message = message.reply_to_message
    text_to_speak = target_message.text or target_message.caption

    if not text_to_speak:
        await message.reply_text("⚠️ Il messaggio selezionato non contiene testo da leggere.")
        return

    processing_msg = await message.reply_text("🎙️ *Sto generando l'audio...*", parse_mode="Markdown")

    bot_token = context.bot.token
    chat_id = update.effective_chat.id

    try:
        await send_voice_message(bot_token, chat_id, text_to_speak)
        await processing_msg.delete()
    except Exception as e:
        await processing_msg.edit_text(f"❌ Errore durante la generazione dell'audio: {e}")


async def status_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestore del comando /status"""
    status_text = get_system_status()
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def route_message_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper per tracciare il Task asincrono e permetterne la cancellazione tramite /stop."""
    # Salva il task corrente per poterlo cancellare
    task = asyncio.current_task()
    context.user_data["current_task"] = task

    try:
        await route_message(update, context)
    except asyncio.CancelledError:
        print("⚠️ Operazione annullata dall'utente tramite /stop.")
    finally:
        # Pulisce il riferimento al task al termine
        context.user_data.pop("current_task", None)


if __name__ == '__main__':
    db_manager.init_db()

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Handlers Comandi
    app.add_handler(CommandHandler("report", progress.show_report))
    app.add_handler(CommandHandler("erase", system.erase_command))
    app.add_handler(CommandHandler("rubrica", show_rubrica))
    app.add_handler(CommandHandler("addcontact", add_contact))
    app.add_handler(CommandHandler("memory", system.show_memory))
    app.add_handler(CommandHandler("web", search.handle_web_search))
    app.add_handler(CommandHandler("vocal", voice_reply_handler))
    app.add_handler(CommandHandler("voice", voice_reply_handler))
    app.add_handler(CommandHandler("status", status_command_handler))
    app.add_handler(CommandHandler("closepdf", system.close_pdf_command))
    app.add_handler(CommandHandler("stop", system.stop_command))
    app.add_handler(CommandHandler("cancel", system.stop_command))
    app.add_handler(CallbackQueryHandler(system.handle_erase_callback, pattern="^(confirm_erase|cancel_erase)$"))

    # Handler YouTube
    youtube_filter = filters.TEXT & (filters.Regex(r'youtube\.com') | filters.Regex(r'youtu\.be'))
    app.add_handler(MessageHandler(youtube_filter, youtube_summary_handler))

    # Handler Documenti (PDF)
    app.add_handler(MessageHandler(filters.Document.MimeType("application/pdf"), pdf_document_handler))

    # Message e Callback handlers
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), route_message_wrapper))
    app.add_handler(MessageHandler(filters.VOICE, voice.handle_voice))
    app.add_handler(CallbackQueryHandler(handle_email_callback, pattern="^email_"))
    app.add_handler(CallbackQueryHandler(handle_contact_callback, pattern="^del_contact_"))

    print("Bot avviato con Orchestratore Multi-Intent e Scheduler attivo...")
    app.run_polling()