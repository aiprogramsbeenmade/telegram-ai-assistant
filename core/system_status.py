import psutil
import time
import platform
from datetime import datetime


def get_system_status() -> str:
    """Raccoglie le metriche hardware e di sistema e restituisce una stringa formattata."""

    # 1. Utilizzo CPU
    cpu_usage = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count(logical=True)

    # 2. Utilizzo RAM
    ram = psutil.virtual_memory()
    ram_total_gb = round(ram.total / (1024 ** 3), 2)
    ram_used_gb = round(ram.used / (1024 ** 3), 2)
    ram_percent = ram.percent

    # 3. Spazio su Disco (partizione root '/')
    disk = psutil.disk_usage('/')
    disk_total_gb = round(disk.total / (1024 ** 3), 2)
    disk_used_gb = round(disk.used / (1024 ** 3), 2)
    disk_percent = disk.percent

    # 4. Uptime del Server
    boot_time_timestamp = psutil.boot_time()
    uptime_seconds = time.time() - boot_time_timestamp
    uptime_hours = int(uptime_seconds // 3600)
    uptime_minutes = int((uptime_seconds % 3600) // 60)

    # 5. Temperature (se supportate dal sistema/kernel)
    temp_str = ""
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current:
                        temp_str = f"🌡️ *Temperatura CPU:* `{entry.current}°C`\n"
                        break
                if temp_str:
                    break
    except Exception:
        # Alcune architetture o ambienti non espongono le temperature via psutil
        temp_str = ""

    # Indicatore visuale dello stato (Emoji)
    status_emoji = "🟢"
    if ram_percent > 85 or cpu_usage > 90 or disk_percent > 90:
        status_emoji = "🔴"
    elif ram_percent > 70 or cpu_usage > 70 or disk_percent > 80:
        status_emoji = "🟡"

    # Costruzione del messaggio Telegram
    status_message = (
        f"{status_emoji} *STATO DEL SISTEMA - JARVIS*\n"
        f"───────────────────\n"
        f"🖥️ *OS:* `{platform.system()} {platform.release()}`\n"
        f"⏱️ *Uptime:* `{uptime_hours}h {uptime_minutes}m`\n\n"
        f"⚡ *CPU ({cpu_count} core):* `{cpu_usage}%`\n"
        f"🧠 *RAM:* `{ram_used_gb} GB / {ram_total_gb} GB` (`{ram_percent}%`)\n"
        f"💾 *Disco:* `{disk_used_gb} GB / {disk_total_gb} GB` (`{disk_percent}%`)\n"
        f"{temp_str}"
        f"───────────────────\n"
        f"📅 _{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}_"
    )

    return status_message


if __name__ == "__main__":
    # Test rapido da riga di comando
    print(get_system_status())