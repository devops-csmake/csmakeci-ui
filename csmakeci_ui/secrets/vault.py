"""HashiCorp Vault secrets provider (KV v2).

The UI authenticates to Vault and manages secrets directly.
Uses only stdlib urllib — no hvac dependency.

Configuration:
    type: vault
    addr: http://vault.example.com:8200   # or set VAULT_ADDR
    mount: secret                          # KV mount path (default: secret)
    path_prefix: csmakeci                  # prefix under the mount
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from csmakeci_ui.secrets.base import BaseSecretsProvider


class VaultSecretsProvider(BaseSecretsProvider):
    name = "vault"

    def __init__(
        self,
        addr: str | None = None,
        token: str | None = None,
        mount: str = "secret",
        path_prefix: str = "csmakeci",
    ):
        self._addr = (addr or os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")).rstrip("/")
        self._token = token or os.environ.get("VAULT_TOKEN", "")
        self._mount = mount
        self._prefix = path_prefix.strip("/")

    def requires_auth(self) -> bool:
        return True

    def auth_fields(self) -> list[dict[str, str]]:
        return [
            {"name": "addr",  "label": "Vault address", "type": "text"},
            {"name": "token", "label": "Token",         "type": "password"},
        ]

    def authenticate(self, credentials: dict[str, str]) -> bool:
        addr  = credentials.get("addr", "").strip()
        token = credentials.get("token", "").strip()
        if not token:
            raise ValueError("Token is required")
        if addr:
            self._addr = addr.rstrip("/")
        self._token = token
        try:
            self._request("GET", "/v1/auth/token/lookup-self")
        except RuntimeError as e:
            raise ValueError(str(e)) from e
        return True

    def list(self) -> list[dict[str, Any]]:
        try:
            resp = self._request("LIST", f"/v1/{self._mount}/metadata/{self._prefix}")
        except RuntimeError:
            return []
        results = []
        for key in resp.get("data", {}).get("keys", []):
            if not key.endswith("/"):
                results.append({"name": key, "scope_kind": "org", "scope_id": ""})
        return results

    def set(self, name: str, value: str, scope_kind: str = "org", scope_id: str = "", **_) -> None:
        self._request("POST", f"/v1/{self._mount}/data/{self._prefix}/{name}", body={
            "data": {"value": value, "scope_kind": scope_kind, "scope_id": scope_id},
        })

    def delete(self, name: str) -> None:
        self._request("DELETE", f"/v1/{self._mount}/metadata/{self._prefix}/{name}")

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = self._addr + path
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"X-Vault-Token": self._token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read()) if resp.length else {}
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Vault {method} {path} → {e.code}: {e.read().decode(errors='replace')}") from e
        except Exception as e:
            raise RuntimeError(f"Vault unreachable at {self._addr}: {e}") from e
