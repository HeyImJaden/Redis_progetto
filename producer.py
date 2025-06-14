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

    pubsub_channel_name = f"pubsub:{channel}"
    r.publish(pubsub_channel_name, notification_json)
    print(f"Notifica pubblicata sul canale Pub/Sub '{pubsub_channel_name}'")

    zset_key = f"notifications:{channel}"
    r.zadd(zset_key, {notification_json: timestamp})
    print(f"Notifica salvata in '{zset_key}' per persistenza.")

    cutoff_timestamp = timestamp - NOTIFICATION_TTL_SECONDS
    removed_count = r.zremrangebyscore(zset_key, '-inf', cutoff_timestamp)
    if removed_count > 0:
        print(f"Rimosse {removed_count} notifiche vecchie da '{zset_key}'.")

    print("--- Notifica Inviata ---")

if __name__ == "__main__":
    while True:
        create_notification()
        if input("Creare un'altra notifica? (s/n): ").lower() != 's':
            break
    print("Produttore terminato.")
