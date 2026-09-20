import json
from core.llm import llm

ROUTER_PROMPT = """Sei un orchestratore di comandi per un assistente AI. Il tuo compito è analizzare il messaggio dell'utente e scomporlo in una lista JSON di azioni da eseguire.

Categorie di azioni disponibili:
1. "email": Invio, lettura o ricerca di email. (es. "manda una mail a X", "leggi la posta")
2. "reminder": Impostazione di promemoria, avvisi o sveglie. (es. "ricordami di X tra Y minuti")
3. "weather": Informazioni sul meteo o previsioni atmosferiche. (es. "che meteo fa domani?")
4. "maps": Percorsi, distanze, calcolo tempi o indicazioni stradali. (es. "quanto ci metto per andare ad Anagni?")
5. "progress": Registrazione di attività fisiche, studio o abitudini. (es. "oggi ho studiato 2 ore")
6. "pdf_qa": Domande, riassunti o spiegazioni relative ad un documento PDF caricato o attualmente attivo. (es. "cosa dice a pagina 3?", "riassumi il file", "chiarisci il capitolo 2")
7. "chat": Conversazione generale, saluti, spiegazioni o domande generiche che non riguardano un modulo specifico o il PDF attivo.

Formato di output richiesto (SOLO un array JSON di oggetti):
[
  {"intent": "NOME_INTENT", "query": "porzione di testo relativa a questa azione"}
]

Esempi:
Input: "Ciao, ricordami tra 5 minuti di prendere l'integratore, manda una mail a Matteo e dimmi il meteo di domani"
Output:
[
  {"intent": "reminder", "query": "ricordami tra 5 minuti di prendere l'integratore"},
  {"intent": "email", "query": "manda una mail a Matteo"},
  {"intent": "weather", "query": "dimmi il meteo di domani"}
]

Input: "Riassumi quello che c'è scritto nel PDF a pagina 5 e poi dimmi il meteo"
Output:
[
  {"intent": "pdf_qa", "query": "Riassumi quello che c'è scritto nel PDF a pagina 5"},
  {"intent": "weather", "query": "dimmi il meteo"}
]

Input: "Spiegami come funziona l'algoritmo di Dijkstra"
Output:
[
  {"intent": "chat", "query": "Spiegami come funziona l'algoritmo di Dijkstra"}
]

Rispondi ESCLUSIVAMENTE con l'array JSON senza testo aggiuntivo."""


def parse_intents(text: str) -> list[dict]:
    """Scompone il testo dell'utente in una lista di azioni/intenti."""
    prompt = (
        f"<|im_start|>system\n{ROUTER_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\nMessaggio: \"{text}\"<|im_end|>\n"
        f"<|im_start|>assistant\n["
    )

    # Forziamo l'inizio con '[' per costringere l'LLM a generare subito un JSON
    output = llm(prompt, max_tokens=300, temperature=0.1, stop=["<|im_end|>"])
    raw_response = "[" + output["choices"][0]["text"].strip()

    try:
        actions = json.loads(raw_response)
        if isinstance(actions, list) and len(actions) > 0:
            return actions
    except Exception as e:
        print(f"Errore parsing JSON dal router: {e}")

    # Fallback sicuro: considera il messaggio come singola chat generale
    return [{"intent": "chat", "query": text}]