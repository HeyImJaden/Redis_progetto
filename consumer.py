import redis
import time
import json
import threading # Pub/Sub background


# Connessione a Redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print("Connesso a Redis!")
except redis.exceptions.ConnectionError as e:
    print(f"Errore di connessione a Redis: {e}")
    exit()

# Durata (in secondi) da cui recuperare le notifiche persistenti all'avvio (es. 24 ore)
LIMITE_TEMPO_NOTIFICHE = 5 * 60

current_user = None
subscribed_channels_pubsub = {} # Dizionario per tenere traccia degli oggetti PubSub per canale

def display_notification(notification_data, source="Real-time"):
    """Visualizza una notifica formattata."""
    # Se notification_data è una stringa JSON, la parsa
    try:
        # Se notification_data è una stringa JSON, la parsa
        if isinstance(notification_data, str):
            data = json.loads(notification_data)
        else:
            data = notification_data # Già un dizionario

        channel = data.get("channel", "N/A")
        title = data.get("title", "N/A")
        message = data.get("message", "N/A")
        timestamp = data.get("timestamp", time.time())
        readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))

        print(f"\n🔔 [{source}] Notifica da '{channel}' ({readable_time}) 🔔")
        print(f"   Titolo: {title}")
        print(f"   Messaggio: {message}")
        print("-" * 30)

    except json.JSONDecodeError:
        print(f"\n⚠️ Errore: Ricevuto messaggio non JSON: {notification_data}")
    except Exception as e:
        print(f"\n⚠️ Errore nella visualizzazione della notifica: {e}")


def register_user():
    print("\n--- Registrazione Nuovo Utente ---")
    username = input("Scegli un username: ").strip()
    password = input("Scegli una password: ")

    user_key = f"user:{username}"
    if r.exists(user_key):
        print("Username già esistente. Prova con un altro.")
        return False

    hashed_password = generate_password_hash(password)
    r.hmset(user_key, {"password_hash": hashed_password, "channels": ""}) # Inizialmente nessun canale
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

    if check_password_hash(user_data.get("password_hash", ""), password):
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
        return set(filter(None, channels_str.split(','))) # filter(None, ...) per rimuovere stringhe vuote se ci sono
    return set()

def save_user_subscribed_channels(username, channels_set):
    user_key = f"user:{username}"
    r.hset(user_key, "channels", ",".join(list(channels_set)))

def pubsub_listener_thread(pubsub_instance, channel_name):
    """Ascolta i messaggi su un canale Pub/Sub specifico."""
    print(f"  [Thread] In ascolto su Pub/Sub channel: {channel_name}")
    try:
        for message in pubsub_instance.listen():
            if message["type"] == "message":
                display_notification(message["data"], source=f"Live ({channel_name})")
            elif message["type"] == "subscribe":
                print(f"  [Thread] Sottoscritto con successo a {message['channel']}")
            elif message["type"] == "unsubscribe":
                print(f"  [Thread] Annullata sottoscrizione da {message['channel']}")
                break
    except redis.exceptions.ConnectionError:
        print(f"  [Thread] Connessione a Redis persa per il canale {channel_name}. Thread terminato.")
    except Exception as e:
        print(f"  [Thread] Errore nel listener Pub/Sub per {channel_name}: {e}. Thread terminato.")


def subscribe_to_channel(channel_name):
    '''Sottoscrive l'utente a un canale e recupera le notifiche recenti.'''
    global subscribed_channels_pubsub
    if not current_user:
        print("Devi prima fare il login.")
        return

    # Aggiungi alla lista dei canali dell'utente
    user_channels = get_user_subscribed_channels(current_user)
    if channel_name in user_channels:
        print(f"Sei già sottoscritto al canale '{channel_name}'.")
        return

    user_channels.add(channel_name)
    save_user_subscribed_channels(current_user, user_channels)

    # 1. Recupera notifiche recenti dalla Sorted Set
    zset_key = f"notifications:{channel_name}"
    cutoff_timestamp = time.time() - FETCH_NOTIFICATIONS_FROM_SECONDS
    # Ottieni notifiche con score (timestamp) maggiore di cutoff_timestamp
    recent_notifications = r.zrangebyscore(zset_key, cutoff_timestamp, '+inf', withscores=False)
    if recent_notifications:
        print(f"\n--- Notifiche Recenti da '{channel_name}' (ultime {FETCH_NOTIFICATIONS_FROM_SECONDS // 3600} ore) ---")
        for notif_json in recent_notifications:
            display_notification(notif_json, source=f"Storico ({channel_name})")
    else:
        print(f"Nessuna notifica recente trovata per '{channel_name}'.")

    # 2. Sottoscrivi al canale Pub/Sub in un thread separato
    if channel_name not in subscribed_channels_pubsub:
        pubsub_channel_name = f"pubsub:{channel_name}"
        p = r.pubsub(ignore_subscribe_messages=False) # ignore_subscribe_messages=False per vedere messaggi di (un)subscribe
        p.subscribe(pubsub_channel_name)
        subscribed_channels_pubsub[channel_name] = p

        # Avvia il thread listener
        thread = threading.Thread(target=pubsub_listener_thread, args=(p, channel_name), daemon=True)
        thread.start()
        print(f"Sottoscrizione a '{channel_name}' avviata. In ascolto per nuove notifiche...")
    else:
         print(f"Sei già in ascolto su Pub/Sub per '{channel_name}'.")


def unsubscribe_from_channel(channel_name):
    '''Annulla la sottoscrizione dell'utente da un canale e chiude il listener Pub/Sub se attivo.'''


def manage_subscriptions():
    '''Gestisce le sottoscrizioni dell'utente ai canali. Consente di sottoscrivere, annullare e visualizzare i canali.'''
    


def main_consumer_loop():
    '''Loop principale del consumatore. Gestisce l'autenticazione e le sottoscrizioni ai canali.'''
    

if __name__ == "__main__":

    main_consumer_loop()
    
        