"""
Shared slowapi rate-limiter instance.

Imported by main.py (to attach to app.state) and by routers that need
per-endpoint limits. Creating the limiter here avoids circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
