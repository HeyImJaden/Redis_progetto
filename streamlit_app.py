'''import streamlit as st
import redis
import threading
import time

# Impostazioni Streamlit
st.set_page_config(page_title="Notifiche Redis", layout="wide")

# Connessione Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Lista messaggi ricevuti
received_messages = []

# 🔹 Sidebar: scelta canale da ascoltare
st.sidebar.title("🎧 Consumer")
channel_name = st.sidebar.text_input("🛰️ Canale da ascoltare", value="notifiche")

# 🔹 Thread di ascolto Redis Pub/Sub
def subscriber_thread(channel):
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    for msg in pubsub.listen():
        if msg["type"] == "message":
            received_messages.append(f"[{channel}] {msg['data']}")

# 🔹 Avvio thread (solo una volta per canale)
if "subscriber_started" not in st.session_state or st.session_state.get("subscriber_channel") != channel_name:
    if "subscriber_started" in st.session_state:
        st.warning("🔄 Hai cambiato canale. Ricarica la pagina per attivare il nuovo consumer.")
    else:
        thread = threading.Thread(target=subscriber_thread, args=(channel_name,), daemon=True)
        thread.start()
        st.session_state.subscriber_started = True
        st.session_state.subscriber_channel = channel_name

# 🔹 Titolo e sottotitolo
st.title("📢 Dashboard Notifiche Redis")
st.subheader("Producer / Consumer con Interfaccia Grafica")

# 🔹 Sezione Producer
with st.form("message_form"):
    selected_channel = st.text_input("📡 Canale su cui inviare il messaggio", value="notifiche")
    message = st.text_input("✉️ Messaggio da inviare")
    submitted = st.form_submit_button("📨 Invia")
    if submitted and message:
        r.publish(selected_channel, message)
        st.success(f"✅ Messaggio inviato al canale **{selected_channel}**: {message}")

# 🔹 Visualizzazione messaggi ricevuti
st.markdown("## 📬 Messaggi Ricevuti (Live)")
output_area = st.empty()

# 🔁 Aggiornamento ogni secondo
def update_display():
    while True:
        if received_messages:
            latest_msgs = "<br>".join(received_messages[::-1][-10:])
            output_area.markdown(f"### Ultimi Messaggi:<br>{latest_msgs}", unsafe_allow_html=True)
        time.sleep(1)

# 🔹 Avvio aggiornamento live (solo una volta)
if "display_thread_started" not in st.session_state:
    t = threading.Thread(target=update_display, daemon=True)
    t.start()
    st.session_state.display_thread_started = True'''
import streamlit as st
import redis
import time
import json
import threading

# Connessione a Redis
@st.cache_resource
def get_redis():
    return redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

r = get_redis()

NOTIFICATION_TTL_SECONDS = 24 * 60 * 60

st.title("🔔 Gestione Canali e Notifiche")

# --- Funzioni ---
def list_channels(parent="root"):
    result = []

    def recurse(p, level):
        key = "channels:root" if p == "root" else f"channels:{p}"
        children = sorted(r.smembers(key))
        for c in children:
            result.append(("  " * level + "- " + c))
            recurse(c, level + 1)

    recurse(parent, 0)
    return result

def listen_to_channel(channel_name, max_messages=10):
    zset_key = f"notifications:{channel_name}"
    messages = r.zrevrange(zset_key, 0, max_messages - 1)
    return [json.loads(msg) for msg in messages]

# --- Sezione: Crea Canale ---
st.subheader("📡 Crea un Canale")
type_choice = st.radio("Tipo di canale:", ["Principale", "Nodo/Sottocanale"])

if type_choice == "Principale":
    name = st.text_input("Nome canale principale")
    if st.button("Crea canale principale"):
        if name and not r.exists(f"channel:{name}"):
            r.sadd("channels:root", name)
            r.hset(f"channel:{name}", mapping={"name": name, "parent": ""})
            st.success(f"Creato canale principale '{name}'")
        else:
            st.error("Nome mancante o canale già esistente.")
else:
    name = st.text_input("Nome sottocanale")
    parent = st.text_input("Nome del canale padre")
    if st.button("Crea nodo"):
        if name and parent and not r.exists(f"channel:{name}") and r.exists(f"channel:{parent}"):
            r.sadd(f"channels:{parent}", name)
            r.hset(f"channel:{name}", mapping={"name": name, "parent": parent})
            st.success(f"Creato nodo '{name}' come figlio di '{parent}'")
        else:
            st.error("Controlla che nome, padre siano corretti e univoci.")

# --- Sezione: Elenca Canali ---
st.subheader("📂 Elenco Canali")
channels = list_channels()
if channels:
    for ch in channels:
        st.text(ch)
else:
    st.info("Nessun canale disponibile.")

# --- Sezione: Invia Notifica ---
st.subheader("🚀 Invia Notifica")
channel = st.text_input("Canale destinazione", key="notif_channel")
title = st.text_input("Titolo", key="notif_title")
message = st.text_area("Messaggio", key="notif_msg")

if st.button("Invia Notifica"):
    if channel and title and message:
        timestamp = time.time()
        data = {
            "title": title,
            "message": message,
            "timestamp": timestamp,
            "channel": channel
        }
        notif_json = json.dumps(data)
        pubsub_key = f"pubsub:{channel}"
        r.publish(pubsub_key, notif_json)

        zset_key = f"notifications:{channel}"
        r.zadd(zset_key, {notif_json: timestamp})
        r.zremrangebyscore(zset_key, '-inf', timestamp - NOTIFICATION_TTL_SECONDS)

        st.success(f"Notifica inviata al canale '{channel}' e salvata.")
    else:
        st.error("Tutti i campi sono obbligatori per inviare la notifica.")
elif st.button("📥 Ricevi notifiche"):
            st.subheader("Ricezione Notifiche")

            available_channels = list(r.smembers("channels:root"))
            for root in available_channels:
                available_channels += list(r.smembers(f"channels:{root}"))

            selected_channel = st.selectbox("Scegli il canale da cui ricevere notifiche:", sorted(available_channels))

            if st.button("Aggiorna notifiche"):
                with st.spinner("Recupero notifiche..."):
                    notifications = listen_to_channel(selected_channel)
                    if notifications:
                        for n in notifications:
                            st.markdown(f"### 📢 {n['title']}")
                            st.markdown(f"- **Messaggio**: {n['message']}")
                            st.markdown(f"- **Data/Ora**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(n['timestamp']))}")
                            st.markdown("---")
                    else:
                        st.info("Nessuna notifica trovata per questo canale.")

# Sezione nella UI
        
