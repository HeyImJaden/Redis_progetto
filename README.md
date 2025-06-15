# Redis_progetto

Un sistema di notifiche in tempo reale bassu su Redis che supporta sia il pattern Pub/Sub che Redis Streams, con gestione di canali gerarchici e persistenza delle notifiche.

## Come Funziona

```
Producer (invia notifiche) → Redis → Consumer (riceve notifiche)
```

Il sistema ha due versioni:
- **Pub/Sub**: Semplice ma perde messaggi se il consumer è offline
- **Streams**: Più robusto, salva tutti i messaggi

## Installazione

```bash
# Installa Redis
sudo apt-get install redis-server

# Installa dipendenze Python
usare file requirements.txt

# Avvia Redis
redis-server
```

## Utilizzo Rapido

### Versione Pub/Sub

**Terminal 1** (per inviare):
```bash
python producer.py
```

**Terminal 2** (per ricevere):
```bash
python consumer.py
```

### Versione Streams

**Terminal 1** (per inviare):
```bash
python producer_stream.py
```

**Terminal 2** (per ricevere):
```bash
python consumer_stream.py
```

## Esempio Pratico

1. **Crea un canale** (Producer):
   - Scegli opzione 1
   - Crea canale "notizie"

2. **Registrati** (Consumer):
   - Scegli opzione 2
   - Username: mario, Password: 123

3. **Iscriviti al canale** (Consumer):
   - Opzione 1 → Gestisci Iscrizioni
   - Iscriviti a "notizie"

4. **Invia notifica** (Producer):
   - Opzione 3
   - Canale: notizie
   - Titolo: Breaking News
   - Messaggio: Qualcosa è successo!

5. **Ricevi la notifica** (Consumer):
   ```
   [Live] Notifica da 'notizie' (2024-06-15 14:30:25)
      Titolo: Breaking News
      Messaggio: Qualcosa è successo!
   ```

## Struttura dei File

- `producer.py` - Invia notifiche (Pub/Sub)
- `consumer.py` - Riceve notifiche (Pub/Sub)  
- `producer_stream.py` - Invia notifiche (Streams)
- `consumer_stream.py` - Riceve notifiche (Streams)

## Funzionalità

### Producer
- Crea canali e sottocanali
- Invia notifiche
- Visualizza struttura canali

### Consumer  
- Registrazione/Login utenti
- Sottoscrizione a canali
- Ricezione notifiche in tempo reale
- Visualizzazione cronologia messaggi

## Struttura Dati Redis

```
# Utenti - Profilo utente + sottoscrizioni
hash → user:mario → {password: "123", channels: "notizie,sport"}

# Canali (Pub/Sub)
channel → pubsub:sport → Pub/Sub real-time
sorted set → notifications:sport → cronologia messaggi

# Canali (Streams)
stream → stream:sport → tutti i messaggi persistenti

# Gestione Canali
set → channels:root → canali principali
set → channels:tech → sottocanali di tech
hash → channel:tech → metadati canale tech
```

### Struttura Notifica

```json
{
    "title": "Titolo notifica",
    "message": "Corpo del messaggio",
    "timestamp": 1234567890.123,
    "channel": "nome_canale"
}
```

### Struttura Utente

```json
{
    "password": "Qwerty12345!",
    "channels": "canale1,canale2,canale3"
}
```

## Configurazione

Nel codice puoi modificare:

```python
# Connessione Redis
host='localhost', port=6379, db=0

# Tempo di conservazione messaggi
LIMITE_TEMPO_NOTIFICHE = 24 * 60 * 60  # 24 ore
```

## Funzioni

### Producer

#### `crea_canale()`
Crea un nuovo canale principale o sottocanale nella gerarchia.

#### `mostra_canali()`  
Visualizza l'albero completo dei canali disponibili.

#### `crea_notifica()`
Invia una nuova notifica a un canale specifico.

### Consumer

#### `registrazione()` / `login()`
Gestione autenticazione utenti con persistenza su Redis.

#### `iscrizione_canale(channel_name)`
Sottoscrive l'utente a un canale con recupero storico automatico.

#### `disiscrizione_canale(channel_name)`
Rimuove la sottoscrizione e termina listener real-time.

#### `gestisci_iscrizioni()`
Interface completa per gestione sottoscrizioni utente.

### Utility

#### `visualizza_notifiche(notification_data, source)`
Formatter standardizzato per output notifiche.

#### `get_iscrizioni(username)` / `set_iscrizioni(username, channels)`
Gestione persistente delle preferenze utente.

### Gestione Threading

#### `pubsub_listener_thread(pubsub_instance, channel_name)`
Worker thread per ricezione asincrona messaggi Pub/Sub.

#### `stream_listener(channel_name, last_id)`
Worker thread per polling Redis Streams con blocking read.
