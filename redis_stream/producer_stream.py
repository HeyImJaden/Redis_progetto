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

# Struttura canali in Redis:
# - Set 'channels:root' contiene tutti i canali principali
# - Set 'channels:{parent}' contiene i figli di un canale
# - Hash 'channel:{name}' contiene info sul canale (es. nome, padre)

def create_channel():
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

def list_channels(parent="root", level=0):
    if parent == "root":
        canali = r.smembers("channels:root")
    else:
        canali = r.smembers(f"channels:{parent}")
    for c in sorted(canali):
        print("  " * level + f"- {c}")
        list_channels(c, level+1)

def show_channels():
    print("\n--- Elenco Canali e Sottocanali ---")
    list_channels()

def create_notification():
    print("\n--- Crea Nuova Notifica (Redis Streams) ---")
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

    stream_key = f"stream:{channel}"
    r.xadd(stream_key, notification_data)
    print(f"Notifica aggiunta allo stream '{stream_key}'")

    # Pulizia vecchie notifiche (TTL)
    min_id = f"0-{int((timestamp - NOTIFICATION_TTL_SECONDS) * 1000)}"
    r.xtrim(stream_key, minid=min_id, approximate=False)
    print(f"Vecchie notifiche rimosse da '{stream_key}' (oltre {NOTIFICATION_TTL_SECONDS//3600}h)")
    print("--- Notifica Inviata ---")

def main_menu():
    while True:
        print("\n--- Menu Gestione Canali (Streams) ---")
        print("1. Crea canale o nodo")
        print("2. Elenca tutti i canali e sottocanali")
        print("3. Crea e invia notifica (stream)")
        print("4. Esci")
        scelta = input("Scegli un'opzione: ").strip()
        if scelta == '1':
            create_channel()
        elif scelta == '2':
            show_channels()
        elif scelta == '3':
            create_notification()
        elif scelta == '4':
            print("Uscita.")
            break
        else:
            print("Scelta non valida.")

if __name__ == "__main__":
    main_menu()
