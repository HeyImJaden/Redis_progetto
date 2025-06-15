'''import streamlit as st
import redis
import time
import json
import threading

# Connessione a Redis
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

NOTIFICATION_TTL_SECONDS = 24 * 60 * 60

# --- Session State ---
if "pagina_attiva" not in st.session_state:
    st.session_state.pagina_attiva = "🏠 Home"

# --- Funzioni ---
def create_channel_streamlit():
    st.subheader("Crea Canale")
    tipo = st.radio("Tipo di canale", ["Principale", "Sottocanale"])

    if tipo == "Principale":
        name = st.text_input("Nome del canale principale")
        if st.button("Crea canale principale"):
            if not name:
                st.warning("Il nome non può essere vuoto.")
            elif r.exists(f"channel:{name}"):
                st.error("Canale già esistente.")
            else:
                r.sadd("channels:root", name)
                r.hset(f"channel:{name}", mapping={"name": name, "parent": ""})
                st.success(f"Canale principale '{name}' creato.")

    else:
        name = st.text_input("Nome del nodo/sottocanale (es. sport.calcio)")
        parent = st.text_input("Nome del canale padre")
        if st.button("Crea nodo/sottocanale"):
            if not name or not parent:
                st.warning("Nome e padre sono obbligatori.")
            elif r.exists(f"channel:{name}"):
                st.error("Canale già esistente.")
            elif not r.exists(f"channel:{parent}"):
                st.error("Il canale padre specificato non esiste.")
            else:
                r.sadd(f"channels:{parent}", name)
                r.hset(f"channel:{name}", mapping={"name": name, "parent": parent})
                st.success(f"Nodo '{name}' creato come figlio di '{parent}'.")

def list_channels(parent="root", level=0, collected=None):
    if collected is None:
        collected = []
    if parent == "root":
        children = r.smembers("channels:root")
    else:
        children = r.smembers(f"channels:{parent}")
    for c in sorted(children):
        prefix = "\u2003" * level + ("↳ " if level > 0 else "🔷 ")
        collected.append(prefix + c)
        list_channels(c, level+1, collected)
    return collected

def show_channels_streamlit():
    st.subheader("Elenco Canali e Sottocanali")
    canali_formattati = list_channels()
    for voce in canali_formattati:
        st.markdown(voce)

def create_notification_streamlit():
    st.subheader("Crea Nuova Notifica")
    channel = st.text_input("Canale (es. sport, sport.calcio, tecnologia)")
    title = st.text_input("Titolo della notifica")
    message = st.text_area("Messaggio della notifica")

    if st.button("Invia notifica"):
        if not channel or not title or not message:
            st.warning("Tutti i campi sono obbligatori.")
            return

        timestamp = time.time()
        notification_data = {
            "title": title,
            "message": message,
            "timestamp": timestamp,
            "channel": channel
        }

        notification_json = json.dumps(notification_data)

        pubsub_channel_name = f"pubsub:{channel}"
        r.publish(pubsub_channel_name, notification_json)

        zset_key = f"notifications:{channel}"
        r.zadd(zset_key, {notification_json: timestamp})

        cutoff_timestamp = timestamp - NOTIFICATION_TTL_SECONDS
        r.zremrangebyscore(zset_key, '-inf', cutoff_timestamp)

        st.success(f"Notifica pubblicata sul canale '{channel}' e salvata.")

def start_consumer(channel_name, message_placeholder):
    pubsub = r.pubsub()
    pubsub.subscribe(f"pubsub:{channel_name}")

    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['timestamp']))
            with message_placeholder.container():
                st.info(f"\n📨 **{data['title']}**\n{data['message']}\n🕒 {formatted_time}\n")


def receive_notifications():
    st.subheader("Ricevi notifiche in tempo reale")
    channel_name = st.text_input("Inserisci il canale da ascoltare")
    if st.button("Inizia ad ascoltare"):
        message_placeholder = st.empty()
        thread = threading.Thread(target=start_consumer, args=(channel_name, message_placeholder), daemon=True)
        thread.start()
        st.success(f"In ascolto su 'pubsub:{channel_name}'...")

# --- Interfaccia Streamlit ---
st.set_page_config(page_title="Gestione Notifiche Redis", layout="centered")
st.title("🔔 Gestione Canali e Notifiche Redis")

scelta = st.sidebar.radio("Menu", ["🏠 Home", "📦 Crea canale", "📋 Elenca canali", "🔔 Invia notifica", "📥 Ricevi notifiche"],
                           index=["🏠 Home", "📦 Crea canale", "📋 Elenca canali", "🔔 Invia notifica", "📥 Ricevi notifiche"].index(st.session_state.pagina_attiva))
st.session_state.pagina_attiva = scelta

if scelta == "🏠 Home":
    st.write("Benvenuto nell'interfaccia di gestione delle notifiche!")
elif scelta == "📦 Crea canale":
    create_channel_streamlit()
elif scelta == "📋 Elenca canali":
    show_channels_streamlit()
elif scelta == "🔔 Invia notifica":
    create_notification_streamlit()
elif scelta == "📥 Ricevi notifiche":
    receive_notifications()
'''
import streamlit as st
import redis
import threading
import time
import json

# Connessione a Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# TTL delle notifiche
NOTIFICATION_TTL_SECONDS = 24 * 60 * 60

# Stato globale per notifiche ricevute
if "notifications" not in st.session_state:
    st.session_state.notifications = []

# Funzione per ricevere notifiche in background
def start_consumer(channel_name):
    pubsub = r.pubsub()
    pubsub.subscribe(f"pubsub:{channel_name}")
    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            st.session_state.notifications.append(data)

# Lancia il consumer in un thread (una sola volta per sessione)
if "consumer_started" not in st.session_state:
    st.session_state.consumer_started = False

def launch_consumer_thread(channel_name):
    if not st.session_state.consumer_started:
        threading.Thread(target=start_consumer, args=(channel_name,), daemon=True).start()
        st.session_state.consumer_started = True

# Mostra gerarchia dei canali in modo indentato
def list_channels_hierarchical(parent="root", level=0):
    prefix = "  " * level + "├─ "
    if parent == "root":
        channels = r.smembers("channels:root")
    else:
        channels = r.smembers(f"channels:{parent}")
    sorted_channels = sorted(channels)
    for ch in sorted_channels:
        st.markdown(f"{prefix}**{ch}**")
        list_channels_hierarchical(ch, level + 1)

# --- UI ---
st.title("📡 Gestione Notifiche con Redis")

menu = st.sidebar.radio("Navigazione", ["📁 Canali", "✉️ Invia Notifica", "📥 Ricevi Notifiche"])

if menu == "📁 Canali":
    st.header("Crea un nuovo canale")
    tipo = st.radio("Tipo canale", ["Principale", "Sottocanale"])
    name = st.text_input("Nome canale")
    parent = None
    if tipo == "Sottocanale":
        parent = st.text_input("Nome canale padre")

    if st.button("Crea canale"):
        if not name:
            st.error("Il nome non può essere vuoto.")
        elif tipo == "Principale":
            if r.exists(f"channel:{name}"):
                st.warning("Canale già esistente.")
            else:
                r.sadd("channels:root", name)
                r.hset(f"channel:{name}", mapping={"name": name, "parent": ""})
                st.success(f"Canale principale '{name}' creato.")
        else:
            if not parent:
                st.error("Il canale padre è obbligatorio.")
            elif not r.exists(f"channel:{parent}"):
                st.error("Il canale padre non esiste.")
            else:
                r.sadd(f"channels:{parent}", name)
                r.hset(f"channel:{name}", mapping={"name": name, "parent": parent})
                st.success(f"Sottocanale '{name}' creato sotto '{parent}'.")

    st.divider()
    st.subheader("📂 Gerarchia Canali")
    list_channels_hierarchical()

elif menu == "✉️ Invia Notifica":
    st.header("Invia una nuova notifica")

    channel = st.text_input("Canale (es. sport, sport.calcio)")
    title = st.text_input("Titolo")
    message = st.text_area("Messaggio")

    if st.button("Invia notifica"):
        if not channel or not title or not message:
            st.warning("Tutti i campi sono obbligatori.")
        else:
            timestamp = time.time()
            data = {
                "title": title,
                "message": message,
                "timestamp": timestamp,
                "channel": channel
            }
            data_json = json.dumps(data)

            r.publish(f"pubsub:{channel}", data_json)
            r.zadd(f"notifications:{channel}", {data_json: timestamp})

            # Pulisce le vecchie notifiche
            cutoff = timestamp - NOTIFICATION_TTL_SECONDS
            r.zremrangebyscore(f"notifications:{channel}", '-inf', cutoff)

            st.success("✅ Notifica inviata!")

elif menu == "📥 Ricevi Notifiche":
    st.header("📡 Ricezione in tempo reale")

    sel_channel = st.text_input("Nome canale da seguire (es. sport)")
    if st.button("Inizia a ricevere"):
        if not sel_channel:
            st.warning("Inserisci un nome canale.")
        else:
            launch_consumer_thread(sel_channel)
            st.success(f"🔔 In ascolto sul canale '{sel_channel}'...")

    st.subheader("📬 Notifiche ricevute:")
    if st.session_state.notifications:
        for notif in reversed(st.session_state.notifications[-10:]):
            with st.expander(notif['title']):
                st.markdown(f"**Canale:** `{notif['channel']}`")
                st.markdown(f"**Messaggio:** {notif['message']}")
                st.markdown(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(notif['timestamp']))}")
    else:
        st.info("Nessuna notifica ricevuta ancora.")
