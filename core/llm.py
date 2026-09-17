from llama_cpp import Llama
import config

print("Caricamento del modello LLM in RAM...")
llm = Llama(
    model_path=config.MODEL_PATH,
    n_ctx=config.N_CTX,
    n_threads=config.N_THREADS,
    verbose=False
)
print("Modello caricato con successo!")

SYSTEM_PROMPT_FACT = (
    "Sei un sistema che estrae fatti, preferenze e avversioni dell'utente. "
    "Se l'utente esprime un gusto, un'abitudine, un vincolo o un'informazione personale "
    "(es. 'non mi piace X', 'adoro Y', 'sappi che Z', 'sono un W'), "
    "estrai e restituisci SOLO la singola frase sintetica in italiano (es. 'All'utente non piacciono i legumi'). "
    "Se il messaggio è una domanda o un saluto generico, rispondi ESCLUSIVAMENTE 'NONE'."
)
SYSTEM_PROMPT_ROUTER = (
    "Sei il modulo di controllo di un assistente AI. "
    "Analizza la richiesta dell'utente e stabilisci se richiede informazioni in tempo reale, notizie recenti, meteo, dati aggiornati o ricerche sul web.\n"
    "Se serve una ricerca sul web, rispondi ESCLUSIVAMENTE con la parola 'SEARCH:' seguita dai termini di ricerca ideali in italiano o inglese.\n"
    "Se NON serve una ricerca web (es. conversazione generale, domande di cultura generale classica, programmazione, saluti, opinioni), rispondi ESCLUSIVAMENTE 'NONE'."
)


def check_web_intent(user_text: str) -> str | None:
    prompt = (
        f"<|im_start|>system\n{SYSTEM_PROMPT_ROUTER}<|im_end|>\n"
        f"<|im_start|>user\n{user_text}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    output = llm(prompt, max_tokens=40, temperature=0.1, stop=["<|im_end|>"])
    res = output['choices'][0]['text'].strip()

    if res.startswith("SEARCH:"):
        return res.replace("SEARCH:", "").strip()
    return None

def extract_fact(user_text: str) -> str | None:
    prompt = (
        f"<|im_start|>system\n{SYSTEM_PROMPT_FACT}<|im_end|>\n"
        f"<|im_start|>user\n{user_text}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    output = llm(prompt, max_tokens=60, temperature=0.1, stop=["<|im_end|>"])
    fact = output['choices'][0]['text'].strip()
    return None if "NONE" in fact or not fact else fact