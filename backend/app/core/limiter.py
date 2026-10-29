from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance (imported by main.py and by routes that need per-endpoint limits).
limiter = Limiter(key_func=get_remote_address)
