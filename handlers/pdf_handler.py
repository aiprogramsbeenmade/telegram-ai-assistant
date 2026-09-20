import os
from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str, max_pages: int = 30) -> dict:
    """
    Estrae il testo da un file PDF indicizzando per pagina.
    Restituisce un dizionario con metadati e testo estratto.
    """
    if not os.path.exists(pdf_path):
        return {"error": "File non trovato."}

    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)

        extracted_pages = []
        full_text = ""

        # Limitiamo le pagine lette per evitare di saturare la RAM/Contesto del modello locale
        pages_to_read = min(num_pages, max_pages)

        for idx in range(pages_to_read):
            page = reader.pages[idx]
            page_text = page.extract_text() or ""
            extracted_pages.append({
                "page_num": idx + 1,
                "content": page_text.strip()
            })
            full_text += f"\n--- Pagina {idx + 1} ---\n{page_text}"

        return {
            "total_pages": num_pages,
            "pages_read": pages_to_read,
            "full_text": full_text.strip(),
            "pages": extracted_pages
        }

    except Exception as e:
        return {"error": f"Errore durante la lettura del PDF: {str(e)}"}


def format_pdf_prompt(pdf_data: dict, user_query: str, max_chars: int = 4500) -> str:
    context = pdf_data.get("full_text", "")

    if len(context) > max_chars:
        context = context[:max_chars] + "\n\n[... Testo del PDF troncato per limiti di spazio ...]"

    system_instruction = (
        "Sei Jarvis, un assistente tecnico chiaro e conciso. "
        "Rispondi alla domanda dell'utente basandoti ESCLUSIVAMENTE sul testo del PDF fornito.\n"
        "REGOLE RIGIDE:\n"
        "- Sii schematico e usa elenchi puntati.\n"
        "- Non ripetere le stesse frasi o concetti.\n"
        "- Se il testo contiene formule o dettagli tecnici su BJT/specchi di corrente, sintetizzali con precisione."
    )

    prompt = (
        f"<|im_start|>system\n{system_instruction}<|im_end|>\n"
        f"<|im_start|>user\n"
        f"TESTO DOCUMENTO:\n{context}\n\n"
        f"DOMANDA: {user_query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    return prompt


if __name__ == "__main__":
    # Test rapido da riga di comando
    test_pdf = "sample.pdf"
    if os.path.exists(test_pdf):
        res = extract_text_from_pdf(test_pdf)
        print(f"Pagine lette: {res['pages_read']}/{res['total_pages']}")
        print(res["full_text"][:500])  # Anteprima primi 500 caratteri