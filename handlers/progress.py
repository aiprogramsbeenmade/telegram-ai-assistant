import json
from telegram import Update
from telegram.ext import ContextTypes
from core.llm import llm
from database import db_manager
from utils.security import restricted


SYSTEM_PROMPT = (
    "Estrai le attività dal messaggio e rispondi ESCLUSIVAMENTE con un array JSON di oggetti:\n"
    "[{\"categoria\": string, \"dettaglio\": string, \"quantita\": int, \"unita\": string}]\n"
    "Converti le ore in minuti se necessario. Non aggiungere altro testo."
)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str = None):
    text = user_text or (update.message.text if update.message else "")

    if not text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n"
    output = llm(prompt, max_tokens=256, temperature=0.1, stop=["<|im_end|>"])
    raw = output['choices'][0]['text'].strip()

    try:
        data = json.loads(raw)
        if isinstance(data, list) and len(data) > 0:
            salvati = db_manager.save_progress(data)
            risposta = "✅ **Progressi registrati:**\n" + "\n".join(salvati)
        else:
            risposta = "⚠️ Nessuna attività chiara identificata."
    except json.JSONDecodeError:
        risposta = "⚠️ Errore nel formato dati generato dall'AI."

    status_msg = context.user_data.pop("status_msg", None)

    if status_msg:
        # Se c'era un messaggio di attesa, lo modifica con la risposta finale
        await status_msg.edit_text(risposta)
    else:
        # Fallback di sicurezza se per qualche motivo il messaggio non c'era
        await update.message.reply_text(risposta)

@restricted
async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows, oggi = db_manager.get_today_report()
    if not rows:
        await update.message.reply_text("ℹ️ Nessun progresso registrato per oggi.")
        return

    report = f"📊 **Progressi di oggi ({oggi}):**\n\n"
    for r in rows:
        report += f"• **{r[0].capitalize()}**: {r[1]} — {r[2]} {r[3]}\n"

    await update.message.reply_text(report, parse_mode="Markdown")