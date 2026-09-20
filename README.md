# 🤖 Jarvis - Telegram AI Assistant Framework

Un assistente virtuale privato, modulare e autonomo eseguito completamente in locale tramite **llama.cpp** ed interfacciato via Telegram.

## 🌟 Funzionalità Principali

* **🧠 Memoria Dinamica Multi-Livello**:
  * **Short-Term Memory**: Gestione della cronologia conversazionale recente via SQLite.
  * **Long-Term Memory**: Estrazione automatica dei fatti, preferenze e dati personali dell'utente con persisitenza DB.
* **🌐 Ricerca Web Autonoma**: Router d'intenti basato su LLM con integrazione DuckDuckGo (`ddgs`) per consultare informazioni in tempo reale.
* **🔀 Orchestratore Multi-Intent**: Routing dinamico dei comandi verso moduli dedicati (Meteo, Mappe, Promemoria, Email, Contatti, Progressi).
* **📧 Gestione Email & Notifiche**: Integrazione IMAP/SMTP per la lettura e l'invio rapido di e-mail.
* **🔒 Privacy & Architettura Locale**: Nessuna dipendenza da API esterne a pagamento; il modello di linguaggio gira interamente sul server locale.
* **🗣️ Trascrizione di vocali** : Manda un messaggio vocale, verrà trascritto e risponderà alla tua richiesta! 
* **📍 Salvataggio automatico di progressi**: Racconta le cose al tuo assistente e ricorderà per te tutti i tuoi progressi tenendone traccia.
* **🗺️ Integrazione con OpenStreetMap**: Per informazioni geografiche più precise.
* **👤 Personale**: Grazie al `user_id` il bot risponderà solamente a TE.
* **📹 Integrazione modulo Youtube**: Basta inviare un link di un video youtube e riceverete un riassunto strutturato sull'argomento proposto nel video.
* **📄 Comprensione PDF**: Manda un PDF e sarai in grado di fare domande e ricevere risposte sull'argomento.

## 🛠️ Architettura del Progetto

```text
telegram-ai-bot/
├── core/            # Engine LLM, router d'intenti e STT
├── database/        # Gestore SQLite (cronologia e fatti utente)
├── handlers/        # Moduli operativi (chat, web, mail, meteo, mappe, system, voice)
├── .env.example     # Struttura delle variabili d'ambiente
├── config.py        # Caricamento e parsing delle configurazioni
├── main.py          # Entrypoint, scheduler e Application Builder di Telegram
└── requirements.txt # Dipendenze Python del progetto
```

## 🚀 Guida all'Installazione

### 1. Clona la repository
```bash
git clone https://github.com/aiprogramsbeenmade/telegram-ai-assistant.git
cd telegram-ai-assistant
```

### 2. Configura l'ambiente virtuale
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installa le dipendenze
```bash
pip3 install --upgrade pip setuptools wheel
pip3 install -r requirements.txt
```

### 4. Installa l'LLM
Io, disponendo di un PC molto datato ho installato Qwen2.5 da 1.5B parametri. Voi potete installare quello che volete. Ai fini della guida continuerò ad installare il mio modello.
```bash
mkdir -p models
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
  qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --local-dir models \
  --local-dir-use-symlinks False
```

Ora procediamo con l'installazione di Whisper per i file audio.
```bash
sudo apt update && sudo apt install ffmpeg -y
cd models/
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
```

Quando avrà finito il make:
```bash
bash ./models/download-ggml-model.sh small
cp models/ggml-base.bin ../models/
```

Modificare eventualmente i file `core/llm.py` e `core/stt.py`.

### 5. Creare il bot telegram
Inizia creando il file .env, segui la struttura mostrata in `.env.example`
La procedura per il bot è molto semplice.
- scrivi a `@BotFather` su telegram;
- manda `/newbot`;
- segui la procedura che ti da;
- copia il token e incollalo nel tuo file `.env`;

Successivamente:
- scrivi a `@userinfobot`;
- manda un messaggio;
- copia il tuo user id e inseriscilo nel `.env`;

Finisci la compilazione del `.env` con tutto quello richiesto.

### 6. Controllo
Controlla di aver inserito tutto il necessario facendo
```bash
python3 config.py
```

### 7. Avvio
Se tutto risulta implementato correttamente puoi avviare il bot!
```bash
python3 main.py
```

## 👾 Comandi integrati nel Bot
- `/stop` : Comando per fermare qualsiasi attività del BOT.
- `/report` : Crea un report dei tuoi progressi memorizzati;
- `/erase` : Elimina il contenuto di TUTTI i database;
- `/rubrica` : Stampa a schermo la rubrica delle Mail;
- `/addcontact` : Utile per memorizzare al volo un contatto mail. UTILIZZO: `/addcontact {nome} {email@example.com}`
- `/web` : Ricerca web rapida con riassunto da parte dell'LLM;
- `/memory` : Controlla cosa ha memorizzato l'IA nella memoria a breve e lungo termine.
- `/vocal` : Rispondendo ad un messaggio verrà generata una traccia audio utilizzando `gTTS`.
- `/status` : Per avere un recap completo dello stato della macchina.



## ⚖️ LICENZA
Questo progetto è sotto licenza GNU GPLv3. Per ulteriori informazioni leggere il file `LICENSE`
