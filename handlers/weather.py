import asyncio
import string
import requests
from telegram import Update
from telegram.ext import ContextTypes
from core.llm import llm
from utils.security import restricted

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Mappa dei codici WMO per le condizioni meteo
WMO_CODES = {
    0: "Cielo sereno",
    1: "Prevalentemente sereno",
    2: "Parzialmente nuvoloso",
    3: "Coperto",
    45: "Nebbia",
    48: "Nebbia brinata",
    51: "Pioggerella leggera",
    61: "Pioggia moderata",
    63: "Pioggia forte",
    71: "Neve leggera",
    80: "Rovesci di pioggia",
    95: "Temporale",
}


def get_coordinates(city_name: str):
    """Recupera latitudine e longitudine di una città."""
    params = {"name": city_name, "count": 1, "language": "it", "format": "json"}
    try:
        response = requests.get(GEOCODING_URL, params=params, timeout=5)
        data = response.json()
        if data.get("results"):
            location = data["results"][0]
            return {
                "name": location.get("name"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "country": location.get("country", ""),
            }
    except Exception as e:
        print(f"Errore geocoding: {e}")
    return None


def fetch_weather(lat: float, lon: float):
    """Ottiene i dati meteo attuali dalle coordinate."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "timezone": "auto",
    }
    try:
        response = requests.get(WEATHER_URL, params=params, timeout=5)
        return response.json().get("current_weather")
    except Exception as e:
        print(f"Errore fetch meteo: {e}")
    return None


@restricted
async def handle(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str = None
):
    text = user_text or (update.message.text if update.message else "")
    text_lower = text.lower()
    city = None

    # Estrazione della città dopo ' a ' o ' ad '
    for prep in [" ad ", " a "]:
        if prep in text_lower:
            parts = text_lower.split(prep, 1)
            if len(parts) > 1 and parts[1].strip():
                raw_city = parts[1].strip().split()[0]
                city = raw_city.strip(string.punctuation).capitalize()
                break

    if not city:
        await update.message.reply_text("📍 Per quale città vuoi sapere il meteo?")
        return

    coords = get_coordinates(city)
    if not coords:
        await update.message.reply_text(
            f"❌ Non sono riuscito a trovare la località: **{city}**",
            parse_mode="Markdown",
        )
        return

    weather = fetch_weather(coords["latitude"], coords["longitude"])
    if not weather:
        await update.message.reply_text(
            "❌ Impossibile recuperare i dati meteo al momento."
        )
        return

    code = weather.get("weathercode", 0)
    condition_desc = WMO_CODES.get(code, "Variabile")

    # Prepariamo il prompt formattato in stile Qwen/ChatML come nel tuo chat.py
    prompt_content = f"""L'utente ha chiesto informazioni sul meteo: "{text}".
Ecco i dati in tempo reale recuperati tramite API per {coords['name']} ({coords['country']}):
- Condizioni: {condition_desc}
- Temperatura attuale: {weather.get('temperature')}°C
- Vento: {weather.get('windspeed')} km/h

Rispondi all'utente in modo sintetico, cordiale ed elegante. Fornisci le informazioni meteo e dai un consiglio rapido se utile (es. come vestirsi o se prendere l'ombrello)."""

    full_prompt = f"<|im_start|>system\nSei Jarvis, un assistente virtuale sintetico, cordiale e preciso. Rispondi in italiano.<|im_end|>\n<|im_start|>user\n{prompt_content}<|im_end|>\n<|im_start|>assistant\n"

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Invocazione sincrona eseguita in un thread dedicato per non bloccare l'event loop
    output = await asyncio.to_thread(
        llm, full_prompt, max_tokens=256, temperature=0.7, stop=["<|im_end|>"]
    )

    risposta = output["choices"][0]["text"].strip()
    status_msg = context.user_data.pop("status_msg", None)

    if status_msg:
        # Se c'era un messaggio di attesa, lo modifica con la risposta finale
        await status_msg.edit_text(risposta)
    else:
        # Fallback di sicurezza se per qualche motivo il messaggio non c'era
        await update.message.reply_text(risposta)