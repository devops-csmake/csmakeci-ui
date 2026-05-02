"""Local filesystem secrets provider.

Uses the same directory csmake reads for local secrets so both tools
share one store without duplication.  Defaults to ~/.csmake/secrets/.

Each secret is a plain file named after the secret.  A sidecar
<name>.meta (JSON) holds scope and timestamp.  Directory is created
0700 on first write.
"""
from __future__ import annotations

import json
import pathlib
import time
from typing import Any

from csmakeci_ui.secrets.base import BaseSecretsProvider

DEFAULT_DIR = pathlib.Path.home() / ".csmake" / "secrets"


class LocalSecretsProvider(BaseSecretsProvider):
    name = "local"

    def __init__(self, secrets_dir: str | pathlib.Path | None = None):
        self._dir = pathlib.Path(secrets_dir or DEFAULT_DIR).expanduser().resolve()

    def _ensure_dir(self):
        self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    def _value_path(self, name: str) -> pathlib.Path:
        return self._dir / _safe(name)

    def _meta_path(self, name: str) -> pathlib.Path:
        return self._dir / (_safe(name) + ".meta")

    def list(self) -> list[dict[str, Any]]:
        if not self._dir.exists():
            return []
        results = []
        for p in sorted(self._dir.iterdir()):
            if p.suffix == ".meta" or not p.is_file():
                continue
            meta = _read_meta(self._meta_path(p.name))
            results.append({
                "name": p.name,
                "scope_kind": meta.get("scope_kind", "org"),
                "scope_id": meta.get("scope_id", ""),
                "created_at": meta.get("created_at") or p.stat().st_mtime,
            })
        return results

    def set(self, name: str, value: str, scope_kind: str = "org", scope_id: str = "", **_) -> None:
        self._ensure_dir()
        vp = self._value_path(name)
        vp.write_text(value)
        vp.chmod(0o600)
        mp = self._meta_path(name)
        meta = _read_meta(mp)
        meta.setdefault("created_at", time.time())
        meta["scope_kind"] = scope_kind
        meta["scope_id"] = scope_id
        mp.write_text(json.dumps(meta))
        mp.chmod(0o600)

    def delete(self, name: str) -> None:
        for p in (self._value_path(name), self._meta_path(name)):
            if p.exists():
                p.unlink()


def _safe(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    if not safe:
        raise ValueError(f"Invalid secret name: {name!r}")
    return safe


def _read_meta(path: pathlib.Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}
