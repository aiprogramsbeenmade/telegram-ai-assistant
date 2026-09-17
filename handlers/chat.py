import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from core.llm import llm, extract_fact, check_web_intent
from handlers.search import search_ddg
from database import db_manager

BASE_SYSTEM_PROMPT = (
    "Sei Jarvis, un assistente virtuale sintetico, cordiale e preciso. Rispondi in italiano.\n"
    "Usa le 'INFORMAZIONI NOTEVOLI SULL'UTENTE' per rispondere a qualsiasi domanda riguardante "
    "i suoi gusti, le sue preferenze e i suoi dati personali."
)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str = None):
    text = user_text or (update.message.text if update.message else "")
    user_id = update.effective_user.id

    if not text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 1. Estrazione eventuale fatto a lungo termine
    new_fact = extract_fact(text)
    if new_fact:
        db_manager.save_fact(user_id, new_fact)

    # 2. Controllo Intent Ricerca Web
    web_query = check_web_intent(text)
    web_context = ""
    if web_query:
        # Recupera il messaggio "Sto pensando..." creato dal main e aggiornalo
        status_msg = context.user_data.get("status_msg")
        if status_msg:
            await status_msg.edit_text(f"🌐 *Ricerca sul web per:* `{web_query}`...", parse_mode="Markdown")

        search_results = await asyncio.to_thread(search_ddg, web_query)
        web_context = f"\n\n[RISULTATI RICERCA WEB PER '{web_query}']:\n{search_results}\n"

        if status_msg:
            await status_msg.edit_text("✍️ *Elaborazione risposte dai risultati web...*", parse_mode="Markdown")

    # 3. Costruzione System Prompt con dati utente e contesto Web
    user_facts = db_manager.get_user_facts(user_id)
    system_prompt = BASE_SYSTEM_PROMPT

    if user_facts:
        facts_formatted = "\n".join([f"- {f}" for f in user_facts])
        system_prompt += (
            f"\n\nPROFILO E PREFERENZE DELL'UTENTE CON CUI STAI PARLANDO:\n{facts_formatted}\n"
            f"IMPORTANTE: Le informazioni sopra descrivono l'UTENTE, NON te stesso."
        )

    if web_context:
        system_prompt += f"\n\nUsa le seguenti informazioni web aggiornate per rispondere alla domanda dell'utente:\n{web_context}"

    # 4. Recupero memoria a breve termine
    recent_history = db_manager.get_recent_history(user_id=user_id, limit=6)

    # 5. Costruzione Prompt finale ChatML
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
    for msg in recent_history:
        prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
    prompt += f"<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n"

    # 6. Generazione Risposta LLM
    output = await asyncio.to_thread(llm, prompt, max_tokens=350, temperature=0.7, stop=["<|im_end|>"])
    risposta = output['choices'][0]['text'].strip()

    # 7. Salvataggio in cronologia
    db_manager.save_message(user_id=user_id, role="user", content=text)
    db_manager.save_message(user_id=user_id, role="assistant", content=risposta)

    # 8. Invio messaggio
    status_msg = context.user_data.pop("status_msg", None)
    if status_msg:
        await status_msg.edit_text(risposta)
    else:
        await update.message.reply_text(risposta)