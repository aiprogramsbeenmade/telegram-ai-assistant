from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db_manager
from utils.security import restricted

@restricted
async def erase_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tastiera di conferma inline
    keyboard = [
        [
            InlineKeyboardButton("⚠️ Sì, cancella tutto", callback_data="confirm_erase"),
            InlineKeyboardButton("❌ Annulla", callback_data="cancel_erase")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "❓ **Sei sicuro di voler resettare il database?**\n\n"
        "Questa azione eliminerà permanentemente tutti i **progressi registrati** e i **promemoria salvati**.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

@restricted
async def handle_erase_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  query = update.callback_query
  await query.answer()

  # Estrai l'user_id dall'evento
  user_id = update.effective_user.id

  if query.data == "confirm_erase":
    db_manager.clear_history(user_id)
    db_manager.clear_user_facts(user_id)  # Cancella anche i fatti memorizzati
    await query.edit_message_text(
      "🗑️ **Memoria e dati resettati con successo.**", parse_mode="Markdown"
    )
  elif query.data == "cancel_erase":
    await query.edit_message_text(
      "❌ Operazione annullata. I tuoi dati sono al sicuro."
    )

@restricted
async def show_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 1. Recupera la memoria a lungo termine
    facts = db_manager.get_user_facts(user_id)
    facts_text = "\n".join([f"• {f}" for f in facts]) if facts else "_Nessun fatto salvato_"

    # 2. Recupera la memoria a breve termine (ultimi messaggi)
    history = db_manager.get_recent_history(user_id, limit=6)
    history_text = "\n".join([f"**{m['role'].capitalize()}**: {m['content']}" for m in history]) if history else "_Nessuna cronologia recente_"

    msg = (
        "🧠 **STATO MEMORIA JARVIS**\n\n"
        "📌 **Lungo Termine (Fatti & Preferenze):**\n"
        f"{facts_text}\n\n"
        "💬 **Breve Termine (Ultimi messaggi):**\n"
        f"{history_text}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")