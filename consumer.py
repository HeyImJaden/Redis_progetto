from core import interface, business, persistence
import threading
import redis
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def listener(username, channels):
    pubsub = r.pubsub()
    pubsub.subscribe(*channels)
    print(f"\n📡 In ascolto su: {', '.join(channels)}...\n")

    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            print(f"[{msg['channel']}] {data['title']}: {data['message']}")

def main():
    print("--- LOGIN ---")
    username, password = interface.prompt_login()
    if not business.login_user(username, password):
        print("Utente non trovato. Registrazione...")
        username, password = interface.prompt_registration()
        if not business.register_user(username, password):
            print("Errore: utente già esistente.")
            return

    channels = business.get_user_subscriptions(username)
    if not channels:
        channels = interface.prompt_subscriptions()
        business.subscribe_user(username, channels)

    # Visualizza notifiche recenti
    print("\n--- Notifiche recenti ---")
    recent = business.get_recent_for_user(username)
    for ch, notifs in recent.items():
        for n in notifs:
            print(f"[{ch}] {n['title']}: {n['message']}")

    # Thread listener
    t = threading.Thread(target=listener, args=(username, channels), daemon=True)
    t.start()

    # Mantieni aperto
    input("\nPremi INVIO per uscire...\n")

if __name__ == "__main__":
    main()
