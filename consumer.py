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
    


def subscribe_to_channel(channel_name):
    '''Sottoscrive l'utente a un canale e recupera le notifiche recenti.'''
    


def unsubscribe_from_channel(channel_name):
    '''Annulla la sottoscrizione dell'utente da un canale e chiude il listener Pub/Sub se attivo.'''


def manage_subscriptions():
    '''Gestisce le sottoscrizioni dell'utente ai canali. Consente di sottoscrivere, annullare e visualizzare i canali.'''
    


def main_consumer_loop():
    '''Loop principale del consumatore. Gestisce l'autenticazione e le sottoscrizioni ai canali.'''
    

if __name__ == "__main__":

    main_consumer_loop()
    
        