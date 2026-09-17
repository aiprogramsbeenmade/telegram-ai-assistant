import sqlite3
from datetime import datetime

DB_PATH = "database/assistant.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progressi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            categoria TEXT,
            dettaglio TEXT,
            quantita INTEGER,
            unita TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promemoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            testo TEXT,
            data_ora TEXT,
            inviato INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS contatti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT, -- 'user' o 'assistant'
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
    """)

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fact TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def save_progress(attivita_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    oggi = datetime.now().strftime("%Y-%m-%d")
    salvati = []

    for item in attivita_list:
        cat = item.get("categoria", "generale")
        det = item.get("dettaglio", "-")
        qta = item.get("quantita", 0)
        uni = item.get("unita", "unita")

        cursor.execute(
            "INSERT INTO progressi (data, categoria, dettaglio, quantita, unita) VALUES (?, ?, ?, ?, ?)",
            (oggi, cat, det, qta, uni)
        )
        salvati.append(f"• **{cat.capitalize()}**: {det} ({qta} {uni})")

    conn.commit()
    conn.close()
    return salvati


def get_today_report():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    oggi = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT categoria, dettaglio, quantita, unita FROM progressi WHERE data = ?", (oggi,))
    rows = cursor.fetchall()
    conn.close()
    return rows, oggi


def save_reminder(chat_id: int, testo: str, data_ora: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO promemoria (chat_id, testo, data_ora) VALUES (?, ?, ?)",
        (chat_id, testo, data_ora)
    )
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id

def mark_reminder_sent(reminder_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE promemoria SET inviato = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

def get_pending_reminders():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, chat_id, testo, data_ora FROM promemoria WHERE inviato = 0")
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_all_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM progressi")
    cursor.execute("DELETE FROM promemoria")
    # Reset della sequenza degli ID autoincrementanti
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='progressi'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='promemoria'")
    conn.commit()
    conn.close()

def get_contact_by_email(email: str):
    """Cerca un contatto tramite la sua email."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email FROM contatti WHERE LOWER(email) = LOWER(?)", (email,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_email_by_name(nome: str):
    """Cerca un'email corrispondente al nome specificato."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM contatti WHERE LOWER(nome) LIKE LOWER(?)", (f"%{nome}%",))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_contact(nome: str, email: str):
    """Salva o aggiorna un contatto."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contatti (nome, email) VALUES (?, ?)
        ON CONFLICT(email) DO UPDATE SET nome=excluded.nome
    """, (nome, email))
    conn.commit()
    conn.close()

def get_all_contacts():
    """Restituisce tutti i contatti ordinati per nome."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email FROM contatti ORDER BY nome ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_contact(contact_id: int):
    """Elimina un contatto tramite ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contatti WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()

def save_message(user_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()

def get_recent_history(user_id: int, limit: int = 6):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    # Invertiamo per avere l'ordine cronologico corretto (dal più vecchio al più recente)
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def clear_history(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def save_fact(user_id: int, fact: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_facts (user_id, fact) VALUES (?, ?)", (user_id, fact))
    conn.commit()
    conn.close()

def get_user_facts(user_id: int) -> list[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT fact FROM user_facts WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def clear_user_facts(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_facts WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()