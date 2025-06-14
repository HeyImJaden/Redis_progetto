def prompt_login():
    username = input("Username: ")
    password = input("Password: ")
    return username, password

def prompt_registration():
    print("\n--- Registrazione ---")
    return prompt_login()

def prompt_notification():
    print("\n--- Crea Notifica ---")
    canale = input("Canale (es. sport.calcio): ")
    titolo = input("Titolo: ")
    messaggio = input("Messaggio: ")
    return canale, titolo, messaggio

def prompt_subscriptions():
    print("\n--- Canali a cui iscriversi (virgola tra canali) ---")
    s = input("Es: sport,finanza,tecnologia: ")
    return [c.strip() for c in s.split(",") if c.strip()]