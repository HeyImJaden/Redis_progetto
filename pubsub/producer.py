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


LIMITE_TEMPO_NOTIFICHE = 24 * 60 * 60

# Struttura canali in Redis:
# - Set 'channels:root' contiene tutti i canali principali
# - Set 'channels:{parent}' contiene i figli di un canale
# - Hash 'channel:{name}' contiene info sul canale (es. nome, padre)

def crea_canale():
    print("\n--- Crea Canale ---")
    tipo = input("Vuoi creare un canale principale (p) o un nodo/sottocanale (n)? [p/n]: ").strip().lower()
    if tipo == 'p':
        name = input("Nome del canale principale: ").strip()
        if not name:
            print("Il nome non può essere vuoto.")
            return
        if r.exists(f"channel:{name}"):
            print("Canale già esistente.")
            return
        r.sadd("channels:root", name)
        r.hset(f"channel:{name}", mapping={"name": name, "parent": ""})
        print(f"Canale principale '{name}' creato.")
    elif tipo == 'n':
        name = input("Nome del nodo/sottocanale (es. sport.calcio): ").strip()
        parent = input("Nome del canale padre: ").strip()
        if not name or not parent:
            print("Nome e padre sono obbligatori.")
            return
        if r.exists(f"channel:{name}"):
            print("Canale già esistente.")
            return
        if not r.exists(f"channel:{parent}"):
            print("Il canale padre specificato non esiste.")
            return
        r.sadd(f"channels:{parent}", name)
        r.hset(f"channel:{name}", mapping={"name": name, "parent": parent})
        print(f"Nodo '{name}' creato come figlio di '{parent}'.")
    else:
        print("Scelta non valida.")

def lista_canali(parent="root", level=0):
    if parent == "root":
        canali = r.smembers("channels:root")
    else:
        canali = r.smembers(f"channels:{parent}")
    for c in sorted(canali):
        print("  " * level + f"- {c}")
        lista_canali(c, level+1)

def mostra_canali():
    print("\n--- Elenco Canali e Sottocanali ---")
    lista_canali()

def crea_notifica():
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

    cutoff_timestamp = timestamp - LIMITE_TEMPO_NOTIFICHE
    removed_count = r.zremrangebyscore(zset_key, '-inf', cutoff_timestamp)
    if removed_count > 0:
        print(f"Rimosse {removed_count} notifiche vecchie da '{zset_key}'.")

    print("--- Notifica Inviata ---")

def main_menu():
    while True:
        print("\n--- Menu Gestione Canali ---")
        print("1. Crea canale o nodo")
        print("2. Elenca tutti i canali e sottocanali")
        print("3. Crea e invia notifica")
        print("4. Esci")
        scelta = input("Scegli un'opzione: ").strip()
        if scelta == '1':
            crea_canale()
        elif scelta == '2':
            mostra_canali()
        elif scelta == '3':
            crea_notifica()
        elif scelta == '4':
            print("Uscita.")
            break
        else:
            print("Scelta non valida.")

if __name__ == "__main__":
    main_menu()
