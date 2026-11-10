"""Supabase connection.

We use the *service role* key, which bypasses row-level security, so this
must only ever run on the server, never in the browser.
"""
from functools import lru_cache

from supabase import Client, create_client

from shared.config import get_settings


@lru_cache
def get_db() -> Client:
    s = get_settings()
    return create_client(s.require("SUPABASE_URL"), s.require("SUPABASE_SERVICE_ROLE_KEY"))
