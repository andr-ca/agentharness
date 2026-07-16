"""Plugin registry — tracks registered plugins and capability ownership.

Capabilities are exclusively owned: only one plugin may claim any given
capability ID.  Registration is sorted and deterministic.
"""

from __future__ import annotations

from agentharness.plugins.api import PluginMetadata


class RegistrationError(ValueError):
    """Raised when a plugin cannot be registered."""


class CapabilityConflictError(ValueError):
    """Raised when two plugins attempt to own the same capability."""


class PluginRegistry:
    """An in-memory ordered registry of plugin metadata.

    Listing order is deterministic (sorted by plugin_id).
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginMetadata] = {}
        self._capability_owners: dict[str, str] = {}  # cap_id → plugin_id

    def register(self, meta: PluginMetadata) -> None:
        """Register a plugin.

        Raises RegistrationError if the plugin_id is already registered.
        Raises CapabilityConflictError if any capability is already owned.
        """
        if meta.plugin_id in self._plugins:
            raise RegistrationError(
                f"{meta.plugin_id!r} is already registered"
            )
        for cap in meta.capabilities:
            owner = self._capability_owners.get(cap)
            if owner is not None:
                raise CapabilityConflictError(
                    f"Capability {cap!r} is already owned by {owner!r}"
                )

        self._plugins[meta.plugin_id] = meta
        for cap in meta.capabilities:
            self._capability_owners[cap] = meta.plugin_id

    def list_plugins(self) -> list[PluginMetadata]:
        """Return all registered plugins, sorted by plugin_id."""
        return sorted(self._plugins.values(), key=lambda m: m.plugin_id)

    def get(self, plugin_id: str) -> PluginMetadata:
        """Return metadata for a specific plugin by ID.

        Raises KeyError if the plugin is not registered.
        """
        if plugin_id not in self._plugins:
            raise KeyError(plugin_id)
        return self._plugins[plugin_id]
