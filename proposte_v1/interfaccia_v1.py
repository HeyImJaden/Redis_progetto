import subprocess
import sys
import os

# Percorsi ai file produttore e consumatore
PRODUCER = os.path.join(os.path.dirname(__file__), 'producer.py')
CONSUMER = os.path.join(os.path.dirname(__file__), 'consumer.py')

def main():
    print("--- Interfaccia Sistema Notifiche Redis ---")
    while True:
        print("\n1. Avvia Produttore di notifiche")
        print("2. Avvia Consumatore di notifiche")
        print("3. Esci")
        scelta = input("Scegli un'opzione (1/2/3): ").strip()
        if scelta == '1':
            subprocess.run([sys.executable, PRODUCER])
        elif scelta == '2':
            subprocess.run([sys.executable, CONSUMER])
        elif scelta == '3':
            print("Uscita.")
            break
        else:
            print("Scelta non valida.")

if __name__ == "__main__":
    main()
