import redis
import json
from datetime import datetime, timedelta

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Login & Profilo
def save_user(username, password):
    r.hset(f"user:{username}", mapping={"password": password})

def get_user_password(username):
    return r.hget(f"user:{username}", "password")

def save_subscriptions(username, channels):
    r.delete(f"subs:{username}")
    r.sadd(f"subs:{username}", *channels)

def get_subscriptions(username):
    return r.smembers(f"subs:{username}")

# Notifiche
def push_notification(channel, title, message):
    notif = {
        "timestamp": datetime.utcnow().isoformat(),
        "title": title,
        "message": message
    }
    r.lpush(f"notifiche:{channel}", json.dumps(notif))
    r.ltrim(f"notifiche:{channel}", 0, 49)  # Tieni solo le ultime 50
    r.expire(f"notifiche:{channel}", 14400)  # 4 ore

    r.publish(channel, json.dumps(notif))

def get_recent_notifications(channel, limit=10):
    return [json.loads(n) for n in r.lrange(f"notifiche:{channel}", 0, limit - 1)]
