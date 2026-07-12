import time

_cache = {}

def get(key):
    item = _cache.get(key)

    if item is None:
        return None

    value, expires = item

    if expires < time.time():
        del _cache[key]
        return None

    return value


def set(key, value, ttl=300):
    _cache[key] = (
        value,
        time.time() + ttl
    )