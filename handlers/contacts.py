# handlers/contacts.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db_manager import get_all_contacts, delete_contact, save_contact
import re
from utils.security import restricted


@restricted
async def show_rubrica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contacts = get_all_contacts()
    if not contacts:
        await update.message.reply_text("📖 La tua rubrica è attualmente vuota.")
        return

    text = "📖 **Rubrica Contatti Saved**\n\n"
    keyboard = []

    for cid, nome, email in contacts:
        text += f"• **{nome}**: `{email}`\n"
        # Pulsante per eliminare/gestire rapidamente
        keyboard.append([InlineKeyboardButton(f"❌ Elimina {nome}", callback_data=f"del_contact_{cid}")])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def handle_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("del_contact_"):
        contact_id = int(query.data.split("_")[-1])
        delete_contact(contact_id)
        await query.edit_message_text("🗑️ Contatto eliminato con successo!")

@restricted
async def add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verifichiamo che ci siano abbastanza argomenti (es. /addcontact Mario mario@example.com)
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ **Sintassi non corretta.**\n"
            "Usa il comando così: `/addcontact <nome> <email>`\n\n"
            "ES: `/addcontact Mario mario@example.com`\n"
            "ES (nome composto): `/addcontact \"Mario Rossi\" mario@example.com`",
            parse_mode="Markdown"
        )
        return

    # L'ultimo elemento è l'email, tutti gli elementi precedenti formano il nome
    email = context.args[-1]
    name = " ".join(context.args[:-1]).strip('"\'')

    # Validazione base dell'indirizzo email
    if not re.match(r'[\w\.-]+@[\w\.-]+\.\w+', email):
        await update.message.reply_text("❌ Indirizzo email non valido. Riprova con una mail corretta.")
        return

    try:
        save_contact(name, email)
        await update.message.reply_text(
            f"✅ **Contatto aggiunto in rubrica!**\n\n"
            f"👤 **Nome:** `{name}`\n"
            f"✉️ **Email:** `{email}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Si è verificato un errore durante il salvataggio: {e}")