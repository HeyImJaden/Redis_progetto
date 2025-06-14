from core import persistence

def register_user(username, password):
    if persistence.get_user_password(username):
        return False  # utente già esistente
    persistence.save_user(username, password)
    return True

def login_user(username, password):
    stored = persistence.get_user_password(username)
    return stored == password

def create_notification(channel, title, message):
    persistence.push_notification(channel, title, message)

def subscribe_user(username, channels):
    persistence.save_subscriptions(username, channels)

def get_user_subscriptions(username):
    return persistence.get_subscriptions(username)

def get_recent_for_user(username):
    channels = persistence.get_subscriptions(username)
    all_notifs = {}
    for c in channels:
        all_notifs[c] = persistence.get_recent_notifications(c)
    return all_notifs
