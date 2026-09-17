import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
from database import db_manager
from core.router import parse_intents  # <--- Import aggiornato
from handlers import chat, progress, reminders, emails, system, voice, weather, maps, search
from handlers.emails import handle_email_callback, handle
from handlers.contacts import show_rubrica, add_contact, handle_contact_callback

import os
from functools import wraps
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()

ALLOWED_USER_ID = int(os.getenv("ALLOWED_TELEGRAM_USER_ID", "0"))


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
        elif intent == "chat":
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


if __name__ == '__main__':
    db_manager.init_db()

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("report", progress.show_report))
    app.add_handler(CommandHandler("erase", system.erase_command))
    app.add_handler(CommandHandler("rubrica", show_rubrica))
    app.add_handler(CommandHandler("addcontact", add_contact))
    app.add_handler(CommandHandler("memory", system.show_memory))
    app.add_handler(CommandHandler("web", search.handle_web_search))
    app.add_handler(CallbackQueryHandler(system.handle_erase_callback, pattern="^(confirm_erase|cancel_erase)$"))

    # Message e Callback handlers (rimossa la duplicazione di MessageHandler)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), route_message))
    app.add_handler(MessageHandler(filters.VOICE, voice.handle_voice))
    app.add_handler(CallbackQueryHandler(handle_email_callback, pattern="^email_"))
    app.add_handler(CallbackQueryHandler(handle_contact_callback, pattern="^del_contact_"))

    print("Bot avviato con Orchestratore Multi-Intent e Scheduler attivo...")
    app.run_polling()