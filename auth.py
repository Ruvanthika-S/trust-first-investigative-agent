import hashlib
import json
import os
import re
from pathlib import Path

from cloud_store import CloudStore
from supabase_auth import SupabaseAuth


def _normalize_email(email):
    return (email or "").strip().lower()


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()


def _build_user_entry(email, password):
    salt = os.urandom(16).hex()
    return {
        "email": _normalize_email(email),
        "salt": salt,
        "password_hash": _hash_password(password, salt),
        "profile": {
            "display_name": _normalize_email(email).split("@")[0],
            "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        },
        "history": [],
        "investigations": [],
        "follow_up_chats": {},
    }


def use_cloud_backend():
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    if not url or not key:
        return False
    if url.startswith("https://your") or "your-project" in url or "your-anon-key" in key or key.startswith("your"):
        return False
    return True


def use_supabase_auth():
    return use_cloud_backend()


def _supabase_auth_client():
    return SupabaseAuth()


def load_user_store(store_path=None):
    if use_cloud_backend():
        try:
            cloud_store = CloudStore()
            return cloud_store.load_store()
        except Exception:
            return {}

    resolved_path = store_path or os.getenv("USER_STORE_PATH") or os.path.join(os.path.dirname(__file__), "users.json")
    if not os.path.exists(resolved_path):
        return {}
    try:
        with open(resolved_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        return {}
    return {}


def save_user_store(store, store_path=None):
    if use_cloud_backend():
        try:
            cloud_store = CloudStore()
            cloud_store.save_store(store)
            return os.getenv("SUPABASE_URL")
        except Exception:
            pass

    resolved_path = store_path or os.getenv("USER_STORE_PATH") or os.path.join(os.path.dirname(__file__), "users.json")
    Path(os.path.dirname(resolved_path)).mkdir(parents=True, exist_ok=True)
    with open(resolved_path, "w", encoding="utf-8") as handle:
        json.dump(store, handle, indent=2)
    return resolved_path


def validate_password_strength(password):
    if not password or len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True


def register_user(email, password, store_path=None):
    normalized_email = _normalize_email(email)
    if not normalized_email or not password or not validate_password_strength(password):
        return False

    if use_supabase_auth():
        client = _supabase_auth_client()
        result = client.sign_up(normalized_email, password)
        if result.get("ok"):
            store = load_user_store(store_path)
            if normalized_email in store:
                return True
            store[normalized_email] = _build_user_entry(normalized_email, password)
            save_user_store(store, store_path)
            return True
        return False

    store = load_user_store(store_path)
    if normalized_email in store:
        return False

    store[normalized_email] = _build_user_entry(normalized_email, password)
    save_user_store(store, store_path)
    return True


def authenticate_user(email, password, store_path=None):
    normalized_email = _normalize_email(email)
    if not normalized_email or not password:
        return False

    if use_supabase_auth():
        client = _supabase_auth_client()
        result = client.sign_in(normalized_email, password)
        if result.get("ok"):
            return True
        print("SUPABASE SIGNIN ERROR:", result.get("error"))
        return False

    store = load_user_store(store_path)
    user_entry = store.get(normalized_email)
    if not user_entry:
        return False

    expected_hash = _hash_password(password, user_entry.get("salt", ""))
    return user_entry.get("password_hash") == expected_hash


def reset_password(email, new_password, store_path=None):
    normalized_email = _normalize_email(email)
    if not normalized_email or not validate_password_strength(new_password):
        return False

    store = load_user_store(store_path)
    user_entry = store.get(normalized_email)
    if not user_entry:
        return False

    salt = os.urandom(16).hex()
    user_entry["salt"] = salt
    user_entry["password_hash"] = _hash_password(new_password, salt)
    store[normalized_email] = user_entry
    save_user_store(store, store_path)
    return True


def delete_account(email, password, store_path=None):
    normalized_email = _normalize_email(email)
    if not normalized_email or not password:
        return False

    store = load_user_store(store_path)
    user_entry = store.get(normalized_email)
    if not user_entry:
        return False

    expected_hash = _hash_password(password, user_entry.get("salt", ""))
    if user_entry.get("password_hash") != expected_hash:
        return False

    store.pop(normalized_email, None)
    save_user_store(store, store_path)
    return True
