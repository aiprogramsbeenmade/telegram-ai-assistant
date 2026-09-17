import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Puntiamo al modello 'small' per una precisione nettamente superiore sull'italiano
MODEL_PATH = os.path.join(BASE_DIR, "models", "ggml-small.bin")
WHISPER_PATH = os.path.join(BASE_DIR, "models", "whisper.cpp", "build", "bin", "whisper-cli")

# Prompt di contesto per guidare il decoder sull'italiano e sui comandi tipici
INITIAL_PROMPT = "Trascrizione di un comando vocale in italiano: meteo, email, promemoria, Anagni, Matteo, percorsi, indicazioni."

def transcribe_audio(ogg_path: str) -> str:
    wav_path = ogg_path.replace(".ogg", ".wav")

    try:
        # Conversione .ogg -> .wav 16kHz mono
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        # Esecuzione Whisper.cpp con prompt e senza timestamp nell'output nativo (-nt)
        cmd = [
            WHISPER_PATH,
            "-m", MODEL_PATH,
            "-f", wav_path,
            "-l", "it",
            "-t", "4",
            "-nt",  # Sopprime i timestamp direttamente dall'output di whisper.cpp
            "--prompt", INITIAL_PROMPT
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    except Exception as e:
        print(f"Errore trascrizione Whisper: {e}")
        return ""

    finally:
        for path in [ogg_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)