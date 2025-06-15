import redis
import time
import json
import threading

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
def register_user():
    print("\n--- Registrazione Nuovo Utente ---")
    username = input("Scegli un username: ").strip()
    password = input("Scegli una password: ")
    user_key = f"user:{username}"
    if r.exists(user_key):
        print("Username già esistente. Prova con un altro.")
        return False
    r.hmset(user_key, {"password": password, "channels": ""})
    print(f"Utente '{username}' registrato con successo!")
    return True

def login_user():
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

def get_user_subscribed_channels(username):
    user_key = f"user:{username}"
    channels_str = r.hget(user_key, "channels")
    if channels_str:
        return set(filter(None, channels_str.split(',')))
    return set()

def save_user_subscribed_channels(username, channels_set):
    user_key = f"user:{username}"
    r.hset(user_key, "channels", ",".join(list(channels_set)))

# --- Notifiche ---
def display_notification(data, source="Stream"):
    if isinstance(data, dict):
        notif = data
    elif isinstance(data, str):
        try:
            notif = json.loads(data)
        except:
            notif = {"message": data}
    else:
        notif = {"message": str(data)}
    channel = notif.get("channel", "N/A")
    title = notif.get("title", "N/A")
    message = notif.get("message", "N/A")
    timestamp = notif.get("timestamp", time.time())
    readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(timestamp)))
    print(f"\n🔔 [{source}] Notifica da '{channel}' ({readable_time}) 🔔")
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
                    display_notification(fields, source=f"Live ({channel_name})")
                    last_id = msg_id
        except redis.exceptions.ConnectionError:
            print(f"Connessione persa per {channel_name}. Thread terminato.")
            break
        except Exception as e:
            print(f"Errore nel listener stream per {channel_name}: {e}")
            break

def subscribe_to_channel(channel_name):
    global subscribed_channels, stream_threads
    if not current_user:
        print("Devi prima fare il login.")
        return
    user_channels = get_user_subscribed_channels(current_user)
    is_new = channel_name not in user_channels
    if is_new:
        user_channels.add(channel_name)
        save_user_subscribed_channels(current_user, user_channels)
    # Recupera notifiche storiche
    stream_key = f"stream:{channel_name}"
    cutoff_timestamp = time.time() - LIMITE_TEMPO_NOTIFICHE
    min_id = f"0-{int(cutoff_timestamp * 1000)}"
    messages = r.xrange(stream_key, min=min_id, max='+')
    if messages:
        print(f"\n--- Notifiche Recenti da '{channel_name}' (ultime {LIMITE_TEMPO_NOTIFICHE // 60} min) ---")
        for msg_id, fields in messages:
            display_notification(fields, source=f"Storico ({channel_name})")
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

def unsubscribe_from_channel(channel_name):
    global stream_threads
    if not current_user:
        print("Devi prima fare il login.")
        return
    user_channels = get_user_subscribed_channels(current_user)
    if channel_name not in user_channels:
        print(f"Non sei sottoscritto al canale '{channel_name}'.")
        return
    user_channels.remove(channel_name)
    save_user_subscribed_channels(current_user, user_channels)
    print(f"Sottoscrizione a '{channel_name}' annullata (nota: il thread listener terminerà solo a fine blocco xread)")
    # Non c'è un modo diretto per killare il thread, ma non riceverà più notifiche se non si sottoscrive più
    stream_threads.pop(channel_name, None)

def manage_subscriptions():
    if not current_user:
        print("Devi prima fare il login.")
        return
    while True:
        print("\n--- Gestione Sottoscrizioni (Streams) ---")
        user_channels = get_user_subscribed_channels(current_user)
        if user_channels:
            print("Canali sottoscritti:", ", ".join(user_channels))
        else:
            print("Non sei sottoscritto a nessun canale.")
        print("Listener attivi:", ", ".join(stream_threads.keys()))
        action = input("Cosa vuoi fare? (s: sottoscrivi, u: annulla, l: lista, b: indietro): ").lower()
        if action == 's':
            channel = input("Nome del canale a cui sottoscriverti: ").strip()
            if channel:
                subscribe_to_channel(channel)
        elif action == 'u':
            channel = input("Nome del canale da cui annullare la sottoscrizione: ").strip()
            if channel:
                unsubscribe_from_channel(channel)
        elif action == 'l':
            print("Ricaricamento notifiche storiche per i canali sottoscritti...")
            for ch in user_channels:
                subscribe_to_channel(ch)
        elif action == 'b':
            break
        else:
            print("Azione non valida.")

def main_consumer_loop():
    global current_user
    while not current_user:
        choice = input("Vuoi (l)ogarti o (r)egistrarti? (q per uscire): ").lower()
        if choice == 'l':
            login_user()
        elif choice == 'r':
            register_user()
        elif choice == 'q':
            return
        else:
            print("Scelta non valida.")
    if current_user:
        print(f"\nBenvenuto {current_user}!")
        saved_channels = get_user_subscribed_channels(current_user)
        if saved_channels:
            print("Sottoscrizione automatica ai canali salvati:", ", ".join(saved_channels))
            for channel in saved_channels:
                subscribe_to_channel(channel)
        else:
            print("Nessun canale salvato nel tuo profilo. Vai a 'Gestione Sottoscrizioni' per aggiungerne.")
        while True:
            print("\n--- Menu Consumatore (Streams) ---")
            action = input("Cosa vuoi fare? (m: gestisci sottoscrizioni, q: quit): ").lower()
            if action == 'm':
                manage_subscriptions()
            elif action == 'q':
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
        main_consumer_loop()
    except KeyboardInterrupt:
        print("\nUscita forzata. Pulisco...")
        stream_threads.clear()
    finally:
        print("Programma consumatore chiuso.")
