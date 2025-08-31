import threading
import time
from resource_monitor import ResourceMonitor
import AscendedScout
import bot

def run_ocr():
    try:
        AscendedScout.main()
    except Exception as e:
        print(f"[MAIN] OCR thread error: {e}")

def run_discord_bot():
    try:
        bot.main()
    except Exception as e:
        print(f"[MAIN] BOT thread error: {e}")

if __name__ == "__main__":
    monitor = ResourceMonitor(log_path="../logs/usage.log", interval=10)
    monitor.start()

    ocr_thread = threading.Thread(target=run_ocr, name="OCR", daemon=True)
    ocr_thread.start()

    bot_thread = threading.Thread(target=run_discord_bot, name="DISCORD")
    bot_thread.start()

    try:
        while bot_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Stop.")
    finally:
        monitor.stop()
        print("[MAIN] Bye.")
