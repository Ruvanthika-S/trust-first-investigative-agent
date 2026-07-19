import os
import json
from typing import Optional, Dict, Any

import requests


class SupabaseAuth:
    def __init__(self, url=None, key=None):
        self.url = (url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.key = key or os.getenv("SUPABASE_ANON_KEY") or ""
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def is_configured(self):
        return bool(self.url and self.key)

    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "error": "Supabase credentials are not configured."}
        try:
            response = requests.post(
                f"{self.url}/auth/v1/signup",
                headers=self.headers,
                json={"email": email, "password": password},
                timeout=20,
            )
            payload = response.json() if response.content else {}
            if response.status_code >= 400:
                return {"ok": False, "error": payload.get("msg") or payload.get("error_description") or "signup failed"}
            return {"ok": True, "data": payload}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "error": "Supabase credentials are not configured."}
        try:
            response = requests.post(
                f"{self.url}/auth/v1/token?grant_type=password",
                headers=self.headers,
                json={"email": email, "password": password},
                timeout=20,
            )
            payload = response.json() if response.content else {}
            if response.status_code >= 400:
                return {"ok": False, "error": payload.get("error_description") or payload.get("msg") or "sign in failed"}
            return {"ok": True, "data": payload}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
