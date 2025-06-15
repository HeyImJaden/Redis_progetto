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
def build_channel_tree():
    # Recupera tutti i canali esistenti
    root = list(r.smembers("channels:root"))
    tree = {}

    def add_children(node_name):
        children = r.smembers(f"channels:{node_name}")
        return {child: add_children(child) for child in children}

    for root_channel in sorted(root):
        tree[root_channel] = add_children(root_channel)
    return tree

def render_channel_tree(tree, level=0):
    for name, children in tree.items():
        padding = level * 20  # 20px per livello
        st.markdown(
            f'<div style="padding-left: {padding}px">↳ <strong>{name}</strong></div>',
            unsafe_allow_html=True
        )
        render_channel_tree(children, level + 1)

def list_channels_hierarchical():
    tree = build_channel_tree()
    render_channel_tree(tree)


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

            parts = channel.split('.')
            for i in range(1, len(parts) + 1):
                ch = '.'.join(parts[:i])
                r.publish(f"pubsub:{ch}", data_json)
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
