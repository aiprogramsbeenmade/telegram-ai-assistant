import asyncio
from ddgs import DDGS
from telegram import Update
from telegram.ext import ContextTypes
from core.llm import llm
from handlers.system import restricted

def search_ddg(query: str, max_results: int = 3) -> str:
    """Esegue la ricerca su DuckDuckGo e restituisce i risultati formattati."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "Nessun risultato trovato sul web."

            output = []
            for r in results:
                output.append(f"• Titolo: {r['title']}\n  Snippet: {r['body']}\n  Link: {r['href']}")
            return "\n\n".join(output)
    except Exception as e:
        return f"Errore durante la ricerca: {e}"

@restricted
async def handle_web_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""

    if not query:
        await update.message.reply_text(
            "⚠️ Per favore specifica cosa cercare. Esempio:\n`/web ultime notizie tecnologia`", parse_mode="Markdown")
        return

    status_msg = await update.message.reply_text("🔍 *Ricerca sul web in corso...*", parse_mode="Markdown")

    # 1. Recupera i risultati da DuckDuckGo in thread separato
    search_results = await asyncio.to_thread(search_ddg, query)

    # 2. Prepara il prompt per far sintetizzare i risultati all'LLM
    system_prompt = (
        "Sei Jarvis. Ti sono stati forniti dei risultati di una ricerca sul web appena eseguita. "
        "Sintetizza le informazioni trovate in modo chiaro, preciso e cordiale in italiano, "
        "rispondendo alla richiesta dell'utente."
    )

    prompt = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\nRichiesta: {query}\n\nRisultati Web:\n{search_results}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    # 3. Genera la sintesi con Qwen
    output = await asyncio.to_thread(llm, prompt, max_tokens=350, temperature=0.3, stop=["<|im_end|>"])
    risposta = output['choices'][0]['text'].strip()

    await status_msg.edit_text(risposta)