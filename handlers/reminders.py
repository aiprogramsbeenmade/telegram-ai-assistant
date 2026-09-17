import json
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
from core.llm import llm
from database import db_manager

SYSTEM_PROMPT = (
    "Sei un assistente per l'estrazione di promemoria.\n"
    "Estrai l'evento e calcola la data e ora esatta d'esecuzione considerando la data e l'ora corrente fornita.\n"
    "Rispondi ESCLUSIVAMENTE con un JSON con questa struttura:\n"
    "{\"testo\": string, \"data_ora\": \"YYYY-MM-DD HH:MM:SS\"}\n\n"
    "Non aggiungere introduzioni o markdown fuori dal JSON."
)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str= None):
    text = user_text or (update.message.text if update.message else "")

    if not text:
        return

    chat_id = update.effective_chat.id

    # Forziamo il fuso orario italiano Europe/Rome (UTC+2 in estate)
    tz = ZoneInfo("Europe/Rome")
    ora_attuale_dt = datetime.now(tz)
    ora_attuale_str = ora_attuale_dt.strftime("%Y-%m-%d %H:%M:%S")

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    prompt = (
        f"<|im_start|>system\n{SYSTEM_PROMPT}\nData e ora attuale (Italy): {ora_attuale_str}<|im_end|>\n"
        f"<|im_start|>user\n{text}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    output = llm(prompt, max_tokens=150, temperature=0.1, stop=["<|im_end|>"])
    raw = output['choices'][0]['text'].strip()

    try:
        data = json.loads(raw)
        testo = data.get("testo")
        data_ora_str = data.get("data_ora")

        # Parsettiamo la data e associamo il Timezone italiano
        target_dt = datetime.strptime(data_ora_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)

        # Salvataggio nel DB
        rem_id = db_manager.save_reminder(chat_id, testo, data_ora_str)

        # Programmazione dello scheduler con timezone
        scheduler = context.bot_data["scheduler"]
        scheduler.add_job(
            send_reminder_notification,
            'date',
            run_date=target_dt,
            args=[context.application, chat_id, testo, rem_id],
            id=f"rem_{rem_id}"
        )

        risposta = f"⏰ **Promemoria impostato!**\n\n📌 *{testo}*\n📅 {target_dt.strftime('%d/%m/%Y alle %H:%M')}"

    except (json.JSONDecodeError, KeyError, ValueError):
        risposta = "⚠️ Non sono riuscito a capire la data o l'ora del promemoria. Prova a specificarla meglio (es. *tra 5 minuti*)."

    await update.message.reply_text(risposta, parse_mode="Markdown")


async def send_reminder_notification(app, chat_id, testo, rem_id):
    # Invia la notifica push su Telegram allo scoccare dell'ora
    await app.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 **PROMEMORIA!**\n\n📌 {testo}",
        parse_mode="Markdown"
    )
    db_manager.mark_reminder_sent(rem_id)