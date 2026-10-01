# utils/security.py
import os
from functools import wraps
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes

load_dotenv()

ALLOWED_USER_ID = int(os.getenv("ALLOWED_TELEGRAM_USER_ID", "0"))

def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        
        if user_id != ALLOWED_USER_ID:
            print(f"⚠️ Accesso negato all'ID: {user_id}")
            if update.message:
                await update.message.reply_text("⛔ Non sei autorizzato ad utilizzare questo bot.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Non autorizzato.", show_alert=True)
            return
            
        return await func(update, context, *args, **kwargs)
    return wrapped

