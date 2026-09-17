import os
import re
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.llm import llm
from database.db_manager import get_contact_by_email, get_all_contacts, save_contact
from utils.security import restricted

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("EMAIL_USER")
SENDER_PASSWORD = os.getenv("EMAIL_PASS")
SIGNATURE = "\n\n---\nInviato da Jarvis"

SYSTEM_PROMPT_DRAFT = (
    "Sei un assistente che compone l'email finale per conto dell'utente. "
    "Il tuo compito è generare ESCLUSIVAMENTE il corpo del messaggio diretto al destinatario. "
    "REGOLE RIGIDE:\n"
    "1. Usa ESCLUSIVAMENTE il nome del destinatario fornito nell'istruzione. NON cambiare o storpiare mai il nome.\n"
    "2. Esprimi SOLO ed ESATTAMENTE la richiesta dell'utente senza inventare contesti aggiuntivi (es. scuse non richieste o finti storici di messaggi).\n"
    "3. NON inserire oggetti, preamboli, spiegazioni o firme/saluti di chiusura generici"
)

SYSTEM_PROMPT_REWRITE = (
    "Sei un esperto di comunicazione. Riscrivi la seguente bozza di email rendendola "
    "più fluida, curata, professionale ed efficace, senza modificare i nomi propri. "
    "ELIMINA qualsiasi oggetto, preambolo, spiegazione o firme/saluti di chiusura generici"
    "Restituisci ESCLUSIVAMENTE il nuovo testo del corpo dell'email."
)


def resolve_recipient(text: str) -> tuple[str | None, str | None]:
    """
    Ritorna la coppia (email_address, display_name).
    Cerca prima contatti salvati in rubrica, poi indirizzi email espliciti nel testo.
    """
    text_lower = text.lower()
    contacts = get_all_contacts()

    # 1. Cerca il nome del contatto nella rubrica SQLite
    for _, nome, email in contacts:
        if nome.lower() in text_lower:
            return email, nome

    # 2. Cerca un indirizzo email formattato (es. nome@domain.com)
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if match:
        email = match.group(0)
        return email, email

    return None, None


def generate_draft(user_prompt: str, recipient_name: str = None, previous_draft: str = None) -> str:
    if previous_draft:
        prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT_REWRITE}<|im_end|>\n"
            f"<|im_start|>user\nBozza da migliorare:\n{previous_draft}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        temp = 0.3
    else:
        context_info = f"Il destinatario si chiama '{recipient_name}'." if recipient_name else ""
        prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT_DRAFT}<|im_end|>\n"
            f"<|im_start|>user\n{context_info}\nIstruzione utente: {user_prompt}\n"
            f"Testo email finale:<|im_end|>\n<|im_start|>assistant\n"
        )
        temp = 0.1

    output = llm(prompt, max_tokens=200, temperature=temp, stop=["<|im_end|>"])
    return output['choices'][0]['text'].strip()


def get_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✉️ Invia Email", callback_data="email_send"),
            InlineKeyboardButton("🔄 Riscrivi (Migliora)", callback_data="email_rewrite")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str = None):
    text = user_text or (update.message.text if update.message else "")
    if not text:
        return

    # Recupera il messaggio di attesa generato da main.py (se presente)
    status_msg = context.user_data.pop("status_msg", None)

    # 1. Gestione dello stato di attesa nome contatto
    if context.user_data.get("awaiting_contact_name"):
        if text.startswith("/") or "invia" in text.lower() or "mail" in text.lower():
            context.user_data.pop("awaiting_contact_name", None)
            context.user_data.pop("pending_contact_email", None)
        else:
            new_name = text.strip()
            target_email = context.user_data.get("pending_contact_email")
            if target_email:
                save_contact(new_name, target_email)
                reply_text = f"✅ Contatto salvato in rubrica:\n👤 **{new_name}** ➔ `{target_email}`"
                if status_msg:
                    await status_msg.edit_text(reply_text, parse_mode="Markdown")
                else:
                    await update.message.reply_text(reply_text, parse_mode="Markdown")

                context.user_data.pop("awaiting_contact_name", None)
                context.user_data.pop("pending_contact_email", None)
                return

    # 2. Risoluzione destinatario
    recipient_email, recipient_name = resolve_recipient(text)
    if not recipient_email:
        error_msg = "❌ Non ho trovato alcun indirizzo email o contatto salvato in rubrica nel tuo messaggio."
        if status_msg:
            await status_msg.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return

    # 3. CAMBIO STATO INTERMEDIO: "Sto generando la bozza..."
    if status_msg:
        await status_msg.edit_text("✍️ *Sto generando la bozza dell'email...*", parse_mode="Markdown")
    else:
        status_msg = await update.message.reply_text("✍️ *Sto generando la bozza dell'email...*", parse_mode="Markdown")

    # 4. Generazione della bozza tramite LLM
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    draft = generate_draft(text, recipient_name=recipient_name)

    context.user_data["email_data"] = {
        "recipient": recipient_email,
        "recipient_name": recipient_name or recipient_email,
        "original_prompt": text,
        "current_draft": draft
    }

    display_target = f"{recipient_name} (`{recipient_email}`)" if recipient_name != recipient_email else f"`{recipient_email}`"

    msg_text = (
        f"✉️ **Bozza Email Generata**\n\n"
        f"**Destinatario:** {display_target}\n\n"
        f"**Testo:**\n{draft}\n\n"
        f"Cosa desideri fare?"
    )

    # 5. CAMBIO STATO FINALE: Mostra la bozza definitiva con la tastiera inline
    await status_msg.edit_text(msg_text, parse_mode="Markdown", reply_markup=get_keyboard())

async def handle_email_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    email_data = context.user_data.get("email_data")
    if not email_data:
        await query.edit_message_text("❌ Sessione email scaduta o non valida.")
        return

    if query.data == "email_send":
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            await query.edit_message_text("❌ Credenziali email non caricate correttamente dal file .env.")
            return

        final_body = f"{email_data['current_draft']}{SIGNATURE}"
        recipient = email_data["recipient"]

        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = recipient
            msg['Subject'] = "Comunicazione da Jarvis"
            msg.attach(MIMEText(final_body, 'plain'))

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)

            await query.edit_message_text(
                f"✅ **Email inviata con successo!**\n\n"
                f"**A:** `{recipient}`\n\n"
                f"**Corpo inviato:**\n{final_body}",
                parse_mode="Markdown"
            )

            # Controllo presenza in rubrica post-invio
            existing_contact = get_contact_by_email(recipient)
            if not existing_contact:
                context.user_data["awaiting_contact_name"] = True
                context.user_data["pending_contact_email"] = recipient
                await query.message.reply_text(
                    f"💡 L'indirizzo `{recipient}` non è presente in rubrica.\n"
                    f"**Scrivimi il nome da associare a questo contatto** per memorizzarlo:",
                    parse_mode="Markdown"
                )

            context.user_data.pop("email_data", None)

        except Exception as e:
            await query.edit_message_text(f"❌ Errore durante l'invio dell'email: {e}")

    elif query.data == "email_rewrite":
        await query.edit_message_text("🔄 *Sto riscrivendo l'email in una versione migliore...*", parse_mode="Markdown")
        new_draft = generate_draft(email_data["original_prompt"], previous_draft=email_data["current_draft"])
        context.user_data["email_data"]["current_draft"] = new_draft

        display_target = f"{email_data['recipient_name']} (`{email_data['recipient']}`)" if email_data['recipient_name'] != email_data['recipient'] else f"`{email_data['recipient']}`"

        msg_text = (
            f"✉️ **Nuova Bozza (Migliorata)**\n\n"
            f"**Destinatario:** {display_target}\n\n"
            f"**Testo:**\n{new_draft}\n\n"
            f"Cosa desideri fare?"
        )

        await query.edit_message_text(msg_text, parse_mode="Markdown", reply_markup=get_keyboard())