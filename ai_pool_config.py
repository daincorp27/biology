# AI Pool Configuration
# Configured for a high-speed, multi-account Gemini Free Tier Pool

import os
from dotenv import load_dotenv

# Ensure env vars are available even when this module is imported outside app.py
load_dotenv()


def _get_env_value(name, default=""):
    """Read an env var safely and normalize common .env formatting issues."""
    value = os.getenv(name, default)
    if value is None:
        return default
    normalized = value.strip()
    if not normalized:
        return default
    if (normalized.startswith('"') and normalized.endswith('"')) or (
        normalized.startswith("'") and normalized.endswith("'")
    ):
        normalized = normalized[1:-1].strip()
    if " #" in normalized:
        normalized = normalized.split(" #", 1)[0].strip()
    return normalized

# Dynamic accumulation of all configured account keys from your .env
GEMINI_KEYS_POOL = []
for i in range(1, 11):  # Supports scaling from 1 up to 10 unique account keys
    key_val = _get_env_value(f"GEMINI_API_KEY_{i}")
    if key_val:
        GEMINI_KEYS_POOL.append(key_val)

# Fallback block to ensure backward compatibility if you just have the standard single key set up
if not GEMINI_KEYS_POOL:
    single_key = _get_env_value("GEMINI_API_KEY")
    if single_key:
        GEMINI_KEYS_POOL.append(single_key)

AI_POOL = {
    "settings": {
        "provider_mode": "multi_account_gemini", 
        "gemini_model": _get_env_value("GEMINI_MODEL", "gemini-2.5-flash-lite"), # Using Flash-Lite for ultra-fast, free-tier execution
        "timeout": 10,
        "enable_caching": True,
        "cache_ttl_seconds": 3600,
        "requests_per_minute_limit": 15  # Default safety ceiling per individual key
    }
}