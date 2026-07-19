import os

import requests


class CloudStore:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = (base_url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("SUPABASE_ANON_KEY") or ""
        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def is_configured(self):
        return bool(self.base_url and self.api_key)

    def _table_url(self, table_name):
        return f"{self.base_url}/rest/v1/{table_name}"

    def load_store(self):
        if not self.is_configured():
            return {}
        try:
            response = requests.get(
                self._table_url("users"),
                headers=self.headers,
                params={"select": "email,password_hash,salt,history,follow_up_chats"},
                timeout=15,
            )
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            rows = response.json() or []
            normalized = {}
            for row in rows:
                email = row.get("email")
                if email:
                    normalized[email] = {
                        "email": email,
                        "password_hash": row.get("password_hash"),
                        "salt": row.get("salt"),
                        "history": row.get("history", []),
                        "follow_up_chats": row.get("follow_up_chats", {}),
                    }
            return normalized
        except Exception:
            return {}

    def save_store(self, store):
        if not self.is_configured():
            return False
        try:
            rows = []
            for email, entry in store.items():
                rows.append({
                    "email": email,
                    "password_hash": entry.get("password_hash"),
                    "salt": entry.get("salt"),
                    "history": entry.get("history", []),
                    "follow_up_chats": entry.get("follow_up_chats", {}),
                })
            if not rows:
                return True
            response = requests.post(
                self._table_url("users"),
                headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
                params={"on_conflict": "email"},
                json=rows,
                timeout=15,
            )
            if response.status_code >= 400:
                return False
            return True
        except Exception:
            return False
