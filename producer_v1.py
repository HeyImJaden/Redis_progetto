import redis
import json

# Configurazione base Redis (modifica se necessario)
r = redis.Redis(host='localhost', port=6379, db=0)

CHANNELS_KEY = 'notifiche:canali'  # Set Redis per i canali disponibili

def add_channel(channel):
    """
    Aggiunge un canale (anche gerarchico) all'elenco dei canali disponibili.
    """
    r.sadd(CHANNELS_KEY, channel)

def list_channels():
    """
    Restituisce la lista dei canali disponibili.
    """
    channels = r.smembers(CHANNELS_KEY)
    return sorted([c.decode() for c in channels])

def send_notification(channel, title, message):
    """
    Invia una notifica su un canale specifico (anche gerarchico).
    """
    notification = {
        'title': title,
        'message': message
    }
    r.publish(channel, json.dumps(notification))
    print(f"Notifica inviata su '{channel}': {title} - {message}")

if __name__ == "__main__":
    print("--- Produttore di Notifiche Redis (Pub/Sub) ---")
    print("Esempi di canali: sport, sport.calcio, tecnologia, finanza")
    while True:
        print("\nCanali disponibili:")
        channels = list_channels()
        if channels:
            for idx, ch in enumerate(channels, 1):
                print(f"  {idx}. {ch}")
        else:
            print("  Nessun canale ancora creato.")
        print("\n1. Scegli un canale esistente\n2. Crea un nuovo canale")
        scelta = input("Scegli (1/2): ").strip()
        if scelta == '1' and channels:
            try:
                idx = int(input("Numero canale: ")) - 1
                channel = channels[idx]
            except (ValueError, IndexError):
                print("Scelta non valida.")
                continue
        elif scelta == '2' or not channels:
            channel = input("Nome nuovo canale (es. sport o sport.calcio): ").strip()
            if not channel:
                print("Canale non valido. Riprova.")
                continue
            add_channel(channel)
        else:
            print("Scelta non valida.")
            continue
        title = input("Titolo della notifica: ").strip()
        message = input("Messaggio: ").strip()
        send_notification(channel, title, message)
        cont = input("Inviare un'altra notifica? (s/n): ").strip().lower()
        if cont != 's':
            break
    print("Produttore terminato.")
