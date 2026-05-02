"""Abstract secrets provider interface for csmakeci-ui.

The UI holds connectors to secrets platforms directly.  The server knows
nothing about secrets — csmakeci (the build tool) handles runtime access
during workflow execution.  The UI's role is purely management: list,
add, delete, and authenticate to the platform if required.

New providers are subclasses dropped into this package and registered
in __init__.py.  No changes to the server required.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSecretsProvider(ABC):
    name: str = "base"

    @abstractmethod
    def list(self) -> list[dict[str, Any]]:
        """Return metadata for all secrets — never values.

        Each dict must have: name.
        Optionally: scope_kind, scope_id, created_at.
        """

    @abstractmethod
    def set(self, name: str, value: str, **meta) -> None:
        """Create or update a secret."""

    @abstractmethod
    def delete(self, name: str) -> None:
        """Remove a secret by name."""

    def requires_auth(self) -> bool:
        return False

    def auth_fields(self) -> list[dict[str, str]]:
        """Fields the UI should render for authentication.

        Each dict: {name, label, type} where type is 'text' or 'password'.
        """
        return []

    def authenticate(self, credentials: dict[str, str]) -> bool:
        """Validate credentials and store session state on self.
        Raise ValueError with a user-facing message on failure.
        """
        return True

    def info(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "requires_auth": self.requires_auth(),
            "auth_fields": self.auth_fields(),
        }
