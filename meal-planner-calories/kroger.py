"""Kroger public API: nearest store by ZIP, and product price lookup.
Check developer.kroger.com for current endpoints and rate limits; they change."""
import base64
import os
import time

import requests

BASE = "https://api.kroger.com/v1"


class KrogerClient:
    def __init__(self):
        self.client_id = os.getenv("KROGER_CLIENT_ID")
        self.client_secret = os.getenv("KROGER_CLIENT_SECRET")
        if not (self.client_id and self.client_secret):
            raise RuntimeError("KROGER_CLIENT_ID / KROGER_CLIENT_SECRET are not set. Add them to .env or use Demo mode.")
        self._token, self._expires = None, 0

    def _auth(self):
        if self._token and time.time() < self._expires - 30:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        resp = requests.post(
            f"{BASE}/connect/oauth2/token",
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": "product.compact"},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._expires = time.time() + body.get("expires_in", 1800)
        return self._token

    def _get(self, path, params):
        resp = requests.get(
            f"{BASE}{path}",
            headers={"Authorization": f"Bearer {self._auth()}", "Accept": "application/json"},
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def find_store(self, zip_code):
        data = self._get("/locations", {"filter.zipCode.near": zip_code, "filter.limit": 1}).get("data", [])
        if not data:
            raise RuntimeError(f"No Kroger-family store found near ZIP {zip_code}.")
        loc = data[0]
        addr = loc.get("address", {})
        return {
            "id": loc["locationId"],
            "name": loc.get("name", "Kroger"),
            "address": f"{addr.get('addressLine1', '')}, {addr.get('city', '')}, {addr.get('state', '')}".strip(", "),
        }

    def price(self, term, store_id):
        """Return the first product with a price, or None."""
        data = self._get("/products", {
            "filter.term": term, "filter.locationId": store_id, "filter.limit": 5,
        }).get("data", [])
        for product in data:
            for item in product.get("items", []):
                price = item.get("price") or {}
                regular, promo = price.get("regular"), price.get("promo")
                if regular:
                    on_sale = bool(promo) and promo < regular
                    return {
                        "product": product.get("description", term),
                        "price": float(promo if on_sale else regular),
                        "size": item.get("size", ""),
                        "on_sale": on_sale,
                    }
        return None
