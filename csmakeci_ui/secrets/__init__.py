"""Secrets provider registry for csmakeci-ui.

Usage:
    from csmakeci_ui.secrets import load_provider
    provider = load_provider({"type": "local"})
    provider = load_provider({"type": "vault", "addr": "http://vault:8200"})
"""
from __future__ import annotations

from typing import Any

from csmakeci_ui.secrets.base import BaseSecretsProvider


def load_provider(config: dict[str, Any] | None = None) -> BaseSecretsProvider:
    """Instantiate a provider from a config dict.

    config keys:
      type  — 'local' (default) | 'vault'
      Any remaining keys are passed as kwargs to the provider constructor.
    """
    cfg = dict(config or {})
    kind = cfg.pop("type", "local")

    if kind == "local":
        from csmakeci_ui.secrets.local import LocalSecretsProvider
        return LocalSecretsProvider(**cfg)

    if kind == "vault":
        from csmakeci_ui.secrets.vault import VaultSecretsProvider
        return VaultSecretsProvider(**cfg)

    raise ValueError(f"Unknown secrets provider type: {kind!r}")
