import asyncio
import math
import string
import requests
from telegram import Update
from telegram.ext import ContextTypes
from core.llm import llm
from utils.security import restricted

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_ROUTE_URL = "http://router.project-osrm.org/route/v1/driving/"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Header richiesto dalle policy di OpenStreetMap Nominatim
HEADERS = {"User-Agent": "JarvisTelegramBot/1.0 (local_assistant)"}


def geocode_location(query: str):
    """Cerca le coordinate di un luogo o indirizzo su OpenStreetMap."""
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=5)
        data = r.json()
        if data:
            return {
                "display_name": data[0]["display_name"],
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
            }
    except Exception as e:
        print(f"Errore Geocoding OSM: {e}")
    return None


def calculate_route(start_lat, start_lon, end_lat, end_lon):
    """Calcola distanza e tempo di itinierario via OSRM (Open Source Routing Machine)."""
    url = f"{OSRM_ROUTE_URL}{start_lon},{start_lat};{end_lon},{end_lat}?overview=false"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get("routes"):
            route = data["routes"][0]
            distance_km = round(route["distance"] / 1000, 1)
            duration_min = round(route["duration"] / 60)
            return {"distance_km": distance_km, "duration_min": duration_min}
    except Exception as e:
        print(f"Errore OSRM Routing: {e}")
    return None


@restricted
async def handle_route(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str
):
    """Gestisce le richieste di percorso, distanza o tempo di percorrenza."""
    # Estrazione di origine e destinazione da frasi del tipo "da X a Y" o "distanza tra X e Y"
    text = user_text.lower().strip(string.punctuation)

    origin, destination = None, None

    if " da " in text and " a " in text:
        parts = text.split(" da ", 1)[1].split(" a ", 1)
        if len(parts) == 2:
            origin = parts[0].strip()
            destination = parts[1].strip()
    elif " tra " in text and " e " in text:
        parts = text.split(" tra ", 1)[1].split(" e ", 1)
        if len(parts) == 2:
            origin = parts[0].strip()
            destination = parts[1].strip()

    if not origin or not destination:
        await update.message.reply_text(
            "📍 Per calcolare il percorso specfica origine e destinazione (es. *percorso da Anagni a Roma*).",
            parse_mode="Markdown",
        )
        return

    loc_origin = geocode_location(origin)
    loc_dest = geocode_location(destination)

    if not loc_origin:
        await update.message.reply_text(f"❌ Impossibile trovare l'origine: **{origin}**")
        return
    if not loc_dest:
        await update.message.reply_text(
            f"❌ Impossibile trovare la destinazione: **{destination}**"
        )
        return

    route = calculate_route(
        loc_origin["lat"], loc_origin["lon"], loc_dest["lat"], loc_dest["lon"]
    )
    if not route:
        await update.message.reply_text(
            "❌ Errore nel calcolo del percorso."
        )
        return

    prompt_content = f"""L'utente ha chiesto informazioni sul percorso: "{user_text}".
Dati calcolati da OpenStreetMap/OSRM:
- Partenza: {loc_origin['display_name']}
- Arrivo: {loc_dest['display_name']}
- Distanza stimata: {route['distance_km']} km
- Tempo stimato in auto: {route['duration_min']} minuti

Fornisci una risposta sintetica, amichevole ed elegante."""

    full_prompt = f"<|im_start|>system\nSei Jarvis, un assistente virtuale sintetico e preciso. Rispondi in italiano.<|im_end|>\n<|im_start|>user\n{prompt_content}<|im_end|>\n<|im_start|>assistant\n"

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )
    output = await asyncio.to_thread(
        llm, full_prompt, max_tokens=256, temperature=0.7, stop=["<|im_end|>"]
    )
    risposta = output["choices"][0]["text"].strip()
    await update.message.reply_text(risposta)