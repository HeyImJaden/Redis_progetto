from core import interface, business

def main():
    while True:
        canale, titolo, messaggio = interface.prompt_notification()
        business.create_notification(canale, titolo, messaggio)
        print("✅ Notifica inviata.\n")

if __name__ == "__main__":
    main()
