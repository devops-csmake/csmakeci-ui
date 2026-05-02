"""HTTP client for calling the csmakeci-server API.

Uses only stdlib (urllib) so csmakeci-ui stays dependency-light.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class ServerClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, **params) -> Any:
        url = self._url(path, params)
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except Exception as e:
            raise RuntimeError(f"Server unreachable at {self.base_url}: {e}") from e

    def post(self, path: str, body: dict | None = None) -> Any:
        url = self._url(path)
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            raise RuntimeError(f"POST {path} failed {e.code}: {body_text}") from e

    def delete(self, path: str) -> Any:
        url = self._url(path)
        req = urllib.request.Request(url, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"DELETE {path} failed {e.code}") from e

    def _url(self, path: str, params: dict | None = None) -> str:
        url = self.base_url + path
        if params:
            from urllib.parse import urlencode
            qs = urlencode({k: v for k, v in params.items() if v is not None})
            if qs:
                url += "?" + qs
        return url

    def stream_url(self, run_id: str) -> str:
        """Return the full SSE URL for a run — injected into templates for browser-side EventSource."""
        return f"{self.base_url}/run/{run_id}/stream"
