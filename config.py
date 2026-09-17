import os
from dotenv import load_dotenv

# Carica le variabili contenute nel file .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")

# Altre configurazioni di sistema
MODEL_PATH = "./models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
N_CTX = 2048
N_THREADS = 4

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN non trovato nel file .env!")