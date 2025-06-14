import redis
import json

# Configurazione base Redis (modifica se necessario)
r = redis.Redis(host='localhost', port=6379, db=0)

CHANNELS_KEY = 'notifiche:canali'  # Set Redis per i canali disponibili

def list_channels():
    """
    Restituisce la lista dei canali disponibili.
    """
    channels = r.smembers(CHANNELS_KEY)
    return sorted([c.decode() for c in channels])

def get_subchannels(channels, selected):
    """
    Restituisce tutti i canali che corrispondono o sono sotto-canali del canale selezionato.
    Esempio: se selected = 'sport', include 'sport', 'sport.calcio', 'sport.basket', ...
    """
    return [c for c in channels if c == selected or c.startswith(selected + ".")]

def main():
    print("--- Consumatore di Notifiche Redis (Pub/Sub) ---")
    while True:
        channels = list_channels()
        if not channels:
            print("Nessun canale disponibile. Attendi che il produttore ne crei uno.")
            input("Premi Invio per riprovare...")
            continue
        print("\nCanali disponibili:")
        for idx, ch in enumerate(channels, 1):
            print(f"  {idx}. {ch}")
        scelta = input("\nA quale canale vuoi iscriverti? (numero): ").strip()
        try:
            idx = int(scelta) - 1
            selected = channels[idx]
        except (ValueError, IndexError):
            print("Scelta non valida.")
            continue
        # Chiedi se includere anche i sotto-canali
        include_sub = input(f"Vuoi ricevere anche le notifiche dei sotto-canali di '{selected}'? (s/n): ").strip().lower() == 's'
        if include_sub:
            subchannels = get_subchannels(channels, selected)
        else:
            subchannels = [selected]
        print(f"\nIn ascolto su: {', '.join(subchannels)}\nPremi Ctrl+C per uscire.")
        pubsub = r.pubsub()
        pubsub.subscribe(*subchannels)
        try:
            for msg in pubsub.listen():
                if msg['type'] == 'message':
                    data = json.loads(msg['data'])
                    print(f"\n[Canale: {msg['channel'].decode()}] {data['title']}: {data['message']}")
        except KeyboardInterrupt:
            print("\nUscita dal consumatore.")
            break

if __name__ == "__main__":
    main()
