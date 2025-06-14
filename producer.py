import redis
import time
import json


try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print("Connesso a Redis!")
except redis.exceptions.ConnectionError as e:
    print(f"Errore di connessione a Redis: {e}")
    exit()


NOTIFICATION_TTL_SECONDS = 24 * 60 * 60

def create_notification():
    print("\n--- Crea Nuova Notifica ---")
    channel = input("Canale (es. 'sport', 'sport.calcio', 'tecnologia'): ").strip()
    title = input("Titolo della notifica: ").strip()
    message = input("Messaggio della notifica: ").strip()

    if not channel or not title or not message:
        print("Canale, titolo e messaggio non possono essere vuoti.")
        return

    timestamp = time.time()
    notification_data = {
        "title": title,
        "message": message,
        "timestamp": timestamp,
        "channel": channel
    }


    notification_json = json.dumps(notification_data)
