import redis
import time
import json
import threading # Pub/Sub background

try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print("Connesso a Redis!")
except redis.exceptions.ConnectionError as e:
    print(f"Errore di connessione a Redis: {e}")
    exit()

LIMITE_TEMPO_NOTIFICHE = 5 * 60
current_user = None
subscribed_channels = set()
stream_threads = {}

# --- User Management (come prima) ---
def registrazione():
    print("\n--- Registrazione Nuovo Utente ---")
    username = input("Scegli un username: ").strip()
    password = input("Scegli una password: ")

    user_key = f"user:{username}"
    if r.exists(user_key):
        print("Username già esistente. Prova con un altro.")
        return False
    
    r.hset(user_key, mapping={"password": password, "channels": ""})
    global current_user
    current_user = username
    print(f"Utente '{username}' registrato con successo!")

    return True

def login():
    global current_user
    print("\n--- Login Utente ---")
    username = input("Username: ").strip()
    password = input("Password: ")

    user_key = f"user:{username}"
    user_data = r.hgetall(user_key)

    if not user_data:
        print("Username non trovato.")
        return False
    
    if user_data.get("password") == password:
        current_user = username
        print(f"Login effettuato come '{username}'.")
        return True
    else:
        print("Password errata.")
        return False

def get_iscrizioni(username):
    user_key = f"user:{username}"
    channels_str = r.hget(user_key, "channels")
    if channels_str:
        return set(filter(None, channels_str.split(',')))
    return set()

def set_iscrizioni(username, channels_set):
    user_key = f"user:{username}"
    r.hset(user_key, "channels", ",".join(list(channels_set)))

# --- Notifiche ---
def visualizza_notifiche(notification_data, source="Stream"):
    if isinstance(notification_data, dict):
        data = notification_data
    elif isinstance(notification_data, str):
        try:
            data = json.loads(notification_data)
        except:
            data = {"message": notification_data}
    else:
        data = {"message": str(notification_data)}
    channel = data.get("channel", "N/A")
    title = data.get("title", "N/A")
    message = data.get("message", "N/A")
    timestamp = data.get("timestamp", time.time())
    readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(timestamp)))
    print(f"\n [{source}] Notifica da '{channel}' ({readable_time}) ")
    print(f"   Titolo: {title}")
    print(f"   Messaggio: {message}")
    print("-" * 30)

def stream_listener(channel_name, last_id='$'):
    stream_key = f"stream:{channel_name}"
    print(f"[Thread] In ascolto su stream: {stream_key}")
    while True:
        try:
            results = r.xread({stream_key: last_id}, block=0)
            for key, messages in results:
                for msg_id, fields in messages:
                    visualizza_notifiche(fields, source=f"Live ({channel_name})")
                    last_id = msg_id
        except redis.exceptions.ConnectionError:
            print(f"Connessione persa per {channel_name}. Thread terminato.")
            break
        except Exception as e:
            print(f"Errore nel listener stream per {channel_name}: {e}")
            break

def iscrizione_canale(channel_name):
    global subscribed_channels, stream_threads
    if not current_user:
        print("Devi prima fare il login.")
        return
    
    user_channels = get_iscrizioni(current_user)
    is_new = channel_name not in user_channels
    if is_new:
        user_channels.add(channel_name)
        set_iscrizioni(current_user, user_channels)
    # Recupera notifiche storiche
    stream_key = f"stream:{channel_name}"
    cutoff_timestamp = time.time() - LIMITE_TEMPO_NOTIFICHE
    min_id = f"0-{int(cutoff_timestamp * 1000)}"
    messages = r.xrange(stream_key, min=min_id, max='+')
    if messages:
        print(f"\n--- Notifiche Recenti da '{channel_name}' (ultime {LIMITE_TEMPO_NOTIFICHE // 60} min) ---")
        for msg_id, fields in messages:
            visualizza_notifiche(fields, source=f"Storico ({channel_name})")
    else:
        print(f"Nessuna notifica recente trovata per '{channel_name}'.")
    # Listener live
    if channel_name not in stream_threads:
        t = threading.Thread(target=stream_listener, args=(channel_name, '$'), daemon=True)
        t.start()
        stream_threads[channel_name] = t
        print(f"Sottoscrizione a '{channel_name}' avviata (stream live)...")
    else:
        print(f"Sei già in ascolto su '{channel_name}'.")

def disiscrizione_canale(channel_name):
    global stream_threads
    if not current_user:
        print("Devi prima fare il login.")
        return
    user_channels = get_iscrizioni(current_user)
    if channel_name not in user_channels:
        print(f"Non sei sottoscritto al canale '{channel_name}'.")
        return
    user_channels.remove(channel_name)
    set_iscrizioni(current_user, user_channels)
    print(f"Sottoscrizione a '{channel_name}' annullata (nota: il thread listener terminerà solo a fine blocco xread)")
    # Non c'è un modo diretto per killare il thread, ma non riceverà più notifiche se non si sottoscrive più
    stream_threads.pop(channel_name, None)

def gestisci_iscrizioni():
    if not current_user:
        print("Devi prima fare il login.")
        return
    while True:
        print("\n--- Gestione Sottoscrizioni (Streams) ---")
        user_channels = get_iscrizioni(current_user)
        if user_channels:
            print("Canali sottoscritti:", ", ".join(user_channels))
        else:
            print("Non sei sottoscritto a nessun canale.")
        print("Listener attivi:", ", ".join(stream_threads.keys()))
        scelta = input("Cosa vuoi fare? (1: Iscriviti, 2: Disiscriviti, 3: Lista Notifiche Canali, 4: Vai Indietro): ").lower()
        if scelta == '1':
            channel = input("Inserisci il nome del canale a cui sottoscriverti: ").strip()
            if channel:
                iscrizione_canale(channel)
        elif scelta == '2':
            channel = input("Inserisci il nome del canale da cui annullare la sottoscrizione: ").strip()
            if channel:
                disiscrizione_canale(channel)
        elif scelta == '3':
            print("Caricamento notifiche storiche per i canali sottoscritti...")
            for ch in user_channels:
                iscrizione_canale(ch)
        elif scelta == '4':
            break
        else:
            print("Azione non valida.")

def main_loop():
    global current_user
    while not current_user:
        scelta = input("1. Loggarti 2. Registrarti 3. Uscita: ")
        if scelta == '1':
            login()
        elif scelta == '2':
            registrazione()
        elif scelta == '3':
            return
        else:
            print("Scelta non valida.")
    if current_user:
        print(f"\nBenvenuto {current_user}!")
        saved_channels = get_iscrizioni(current_user)
        if saved_channels:
            print("Sottoscrizione automatica ai canali salvati:", ", ".join(saved_channels))
            for channel in saved_channels:
                iscrizione_canale(channel)
        else:
            print("Nessun canale salvato nel tuo profilo. Vai a 'Gestione Sottoscrizioni' per aggiungerne.")
        while True:
            print("\n--- Menu Consumatore (Streams) ---")
            scelta = input("Cosa vuoi fare? (1. Gestisci Iscrizioni 2. Esci): ").lower()
            if scelta == '1':
                gestisci_iscrizioni()
            elif scelta == '2':
                print("Disconnessione in corso...")
                stream_threads.clear()
                current_user = None
                print("Consumatore terminato.")
                break
            else:
                print("Azione non valida. Le notifiche live continueranno ad arrivare.")
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nUscita forzata. Pulisco...")
        stream_threads.clear()
    finally:
        print("Programma consumatore chiuso.")
