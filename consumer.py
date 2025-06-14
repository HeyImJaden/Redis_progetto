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
    # Evidenziazione visiva per notifiche live
    if source.startswith("Live"):
        print("\n🔔 [Notifica Live] Ricevuta una nuova notifica!")
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

    r.hmset(user_key, {"password": password, "channels": ""}) # Inizialmente nessun canale
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
    is_new_subscription = channel_name not in user_channels
    if is_new_subscription:
        user_channels.add(channel_name)
        save_user_subscribed_channels(current_user, user_channels)

    # 1. Recupera notifiche recenti dalla Sorted Set SOLO se nuova sottoscrizione o richiesto esplicitamente
    if is_new_subscription:
        zset_key = f"notifications:{channel_name}"
        cutoff_timestamp = time.time() - LIMITE_TEMPO_NOTIFICHE
        recent_notifications = r.zrangebyscore(zset_key, cutoff_timestamp, '+inf', withscores=False)
        if recent_notifications:
            print(f"\n--- Notifiche Recenti da '{channel_name}' (ultime {LIMITE_TEMPO_NOTIFICHE // 3600} ore) ---")
            for notif_json in recent_notifications:
                display_notification(notif_json, source=f"Storico ({channel_name})")
        else:
            print(f"Nessuna notifica recente trovata per '{channel_name}'.")

    # 2. Sottoscrivi al canale Pub/Sub in un thread separato SE NON già attivo
    if channel_name not in subscribed_channels_pubsub:
        pubsub_channel_name = f"pubsub:{channel_name}"
        p = r.pubsub(ignore_subscribe_messages=False)
        p.subscribe(pubsub_channel_name)
        subscribed_channels_pubsub[channel_name] = p
        thread = threading.Thread(target=pubsub_listener_thread, args=(p, channel_name), daemon=True)
        thread.start()
        print(f"Sottoscrizione a '{channel_name}' avviata. In ascolto per nuove notifiche...")
    else:
        print(f"Sei già in ascolto su Pub/Sub per '{channel_name}'.")


def unsubscribe_from_channel(channel_name):
    '''Annulla la sottoscrizione dell'utente da un canale e chiude il listener Pub/Sub se attivo.'''
    global subscribed_channels_pubsub
    if not current_user:
        print("Devi prima fare il login.")
        return

    user_channels = get_user_subscribed_channels(current_user)
    if channel_name not in user_channels:
        print(f"Non sei sottoscritto al canale '{channel_name}'.")
        return

    user_channels.remove(channel_name)
    save_user_subscribed_channels(current_user, user_channels)

    if channel_name in subscribed_channels_pubsub:
        pubsub_instance = subscribed_channels_pubsub.pop(channel_name)
        pubsub_channel_name = f"pubsub:{channel_name}"
        try:
            pubsub_instance.unsubscribe(pubsub_channel_name)
            pubsub_instance.close() # Chiude la connessione pubsub
            print(f"Sottoscrizione a '{channel_name}' annullata.")
        except Exception as e:
            print(f"Errore durante l'annullamento della sottoscrizione da {channel_name}: {e}")
    else:
        print(f"Non stavi ascoltando attivamente il canale '{channel_name}' (nessun listener Pub/Sub attivo).")


def manage_subscriptions():
    '''Gestisce le sottoscrizioni dell'utente ai canali. Consente di sottoscrivere, annullare e visualizzare i canali.'''
    if not current_user:
        print("Devi prima fare il login.")
        return

    while True:
        print("\n--- Gestione Sottoscrizioni ---")
        user_channels = get_user_subscribed_channels(current_user)
        if user_channels:
            print("Canali sottoscritti:", ", ".join(user_channels))
        else:
            print("Non sei sottoscritto a nessun canale.")

        print("Attualmente in ascolto (Pub/Sub):", ", ".join(subscribed_channels_pubsub.keys()))

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
            # Ricarica e visualizza notifiche storiche per i canali sottoscritti
            print("Ricaricamento notifiche storiche per i canali sottoscritti...")
            for ch in user_channels:
                 subscribe_to_channel(ch) # Questo recupererà anche le notifiche storiche
        elif action == 'b':
            break
        else:
            print("Azione non valida.")
    


def main_consumer_loop():
    '''Loop principale del consumatore. Gestisce l'autenticazione e le sottoscrizioni ai canali.'''
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
            # Mostra notifiche storiche per tutti i canali sottoscritti
            print("\n--- Notifiche Storiche dai tuoi canali sottoscritti ---")
            for channel in saved_channels:
                zset_key = f"notifications:{channel}"
                cutoff_timestamp = time.time() - LIMITE_TEMPO_NOTIFICHE
                recent_notifications = r.zrangebyscore(zset_key, cutoff_timestamp, '+inf', withscores=False)
                if recent_notifications:
                    print(f"\nCanale '{channel}':")
                    for notif_json in recent_notifications:
                        display_notification(notif_json, source=f"Storico ({channel})")
                else:
                    print(f"Nessuna notifica recente per '{channel}'.")
        else:
            print("Nessun canale salvato nel tuo profilo. Vai a 'Gestione Sottoscrizioni' per aggiungerne.")

        while True:
            print("\n--- Menu Consumatore ---")
            action = input("Cosa vuoi fare? (m: gestisci sottoscrizioni, q: quit): ").lower()
            if action == 'm':
                manage_subscriptions()
            elif action == 'q':
                print("Disconnessione in corso...")
                for channel_name, pubsub_instance in list(subscribed_channels_pubsub.items()):
                    pubsub_channel_name = f"pubsub:{channel_name}"
                    try:
                        print(f"Chiudo listener per {channel_name}")
                        pubsub_instance.unsubscribe(pubsub_channel_name)
                        pubsub_instance.close()
                    except Exception as e:
                        print(f"Errore chiudendo listener per {channel_name}: {e}")
                subscribed_channels_pubsub.clear()
                current_user = None # Logout logico
                print("Consumatore terminato.")
                break
            else:
                print("Azione non valida. Le notifiche live continueranno ad arrivare.")
            time.sleep(0.1)
    

def receive_realtime_notifications(channel_name):
    """
    Riceve notifiche in tempo reale da un canale Pub/Sub specifico.
    Esempio d'uso: receive_realtime_notifications('nome_canale')
    """
    pubsub_channel_name = f"pubsub:{channel_name}"
    p = r.pubsub()
    p.subscribe(pubsub_channel_name)
    print(f"In ascolto su {pubsub_channel_name} per notifiche in tempo reale. Premi Ctrl+C per uscire.")
    try:
        for message in p.listen():
            if message["type"] == "message":
                display_notification(message["data"], source=f"Live ({channel_name})")
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente. Uscita dalla ricezione notifiche.")
    finally:
        p.unsubscribe(pubsub_channel_name)
        p.close()
        print(f"Disiscritto da {pubsub_channel_name}.")


if __name__ == "__main__":
    try:
        main_consumer_loop()
    except KeyboardInterrupt:
        print("\nUscita forzata. Pulisco...")
        # Simile al blocco 'q' nel loop principale per una chiusura pulita
        if current_user and subscribed_channels_pubsub:
            for channel_name, pubsub_instance in list(subscribed_channels_pubsub.items()):
                pubsub_channel_name = f"pubsub:{channel_name}"
                try:
                    pubsub_instance.unsubscribe(pubsub_channel_name)
                    pubsub_instance.close()
                except: pass # Ignora errori in chiusura forzata
            subscribed_channels_pubsub.clear()
    finally:
        print("Programma consumatore chiuso.")