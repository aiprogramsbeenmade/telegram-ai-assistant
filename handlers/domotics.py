import os
import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.security import restricted


load_dotenv()
SHELLY_IP = os.getenv("SHELLY_IP")  # Cambia con l'IP di default se necessario


def get_shelly_status():
    """Recupera lo stato attuale dello Shelly (ON/OFF)."""
    try:
        # Tenta chiamata per Gen 2 / Gen 3 (RPC API)
        url_gen2 = f"http://{SHELLY_IP}/rpc/Switch.GetStatus?id=0"
        r = requests.get(url_gen2, timeout=3)
        if r.status_code == 200:
            data = r.json()
            return "ON" if data.get("output") else "OFF"
    except Exception:
        pass

    try:
        # Fallback per Gen 1 (REST API classic)
        url_gen1 = f"http://{SHELLY_IP}/relay/0"
        r = requests.get(url_gen1, timeout=3)
        if r.status_code == 200:
            data = r.json()
            return "ON" if data.get("ison") else "OFF"
    except Exception as e:
        print(f"Errore connessione Shelly: {e}")

    return "UNREACHABLE"


def set_shelly_state(turn_on: bool):
    """Accende o spegne lo Shelly."""
    state_str = "on" if turn_on else "off"

    # Tentativo Gen 2 / Gen 3
    try:
        url_gen2 = f"http://{SHELLY_IP}/rpc/Switch.Set?id=0&on={'true' if turn_on else 'false'}"
        r = requests.get(url_gen2, timeout=3)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    # Tentativo Gen 1
    try:
        url_gen1 = f"http://{SHELLY_IP}/relay/0?turn={state_str}"
        r = requests.get(url_gen1, timeout=3)
        if r.status_code == 200:
            return True
    except Exception as e:
        print(f"Errore comando Shelly: {e}")

    return False


def build_lights_keyboard(status: str):
    """Crea la tastiera interattiva in base allo stato attuale."""
    status_icon = "🟢 ACCESA" if status == "ON" else ("🔴 SPENTA" if status == "OFF" else "⚠️ NON RAGGIUNGIBILE")

    keyboard = [
        [
            InlineKeyboardButton("💡 Accendi", callback_data="light_on"),
            InlineKeyboardButton("🌙 Spegni", callback_data="light_off"),
        ],
        [
            InlineKeyboardButton("🔄 Aggiorna Stato", callback_data="light_refresh")
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard)
    text = (
        f"🎛️ **Pannello di Controllo Luci Stanza**\n\n"
        f"Stato attuale: **{status_icon}**\n"
        f"IP Dispositivo: `{SHELLY_IP}`"
    )
    return text, markup


@restricted
async def open_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /luci o intent vocale/testuale per aprire il pannello."""
    status = get_shelly_status()
    text, markup = build_lights_keyboard(status)

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


@restricted
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i click sui bottoni del pannello."""
    query = update.callback_query
    await query.answer()  # Notifica a Telegram che il click è stato ricevuto

    data = query.data

    if data == "light_on":
        success = set_shelly_state(True)
        msg = "💡 Luce accesa!" if success else "❌ Impossibile comunicare con lo Shelly."
    elif data == "light_off":
        success = set_shelly_state(False)
        msg = "🌙 Luce spenta!" if success else "❌ Impossibile comunicare con lo Shelly."
    elif data == "light_refresh":
        msg = "🔄 Stato aggiornato!"

    status = get_shelly_status()
    text, markup = build_lights_keyboard(status)

    # Aggiorna il messaggio esistente evitando errori se il testo non è cambiato
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        pass