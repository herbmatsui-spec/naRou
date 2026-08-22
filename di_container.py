from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DIContainer:
    """Simple dependency injection container with singleton support."""

    def __init__(self):
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Callable[[], Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._is_singleton: dict[type, bool] = {}

    def register(
        self,
        service_type: type[T],
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
        singleton: bool = True,
    ) -> None:
        """Register a service.

        Args:
            service_type: The service type/interface.
            factory: Callable that creates the service instance.
            instance: Pre-created instance (overrides factory).
            singleton: Whether to cache the instance as singleton.
        """
        if instance is not None:
            self._singletons[service_type] = instance
            self._is_singleton[service_type] = True
            logger.debug(f"Registered singleton instance: {service_type.__name__}")
        elif factory is not None:
            self._factories[service_type] = factory
            self._is_singleton[service_type] = singleton
            if singleton:
                logger.debug(f"Registered singleton factory: {service_type.__name__}")
            else:
                logger.debug(f"Registered transient factory: {service_type.__name__}")
        else:
            raise ValueError("Either factory or instance must be provided")

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a service instance (singleton if registered as such)."""
        # Check singleton cache first
        if service_type in self._singletons:
            return self._singletons[service_type]

        # Check factories
        if service_type in self._factories:
            factory = self._factories[service_type]
            instance = factory()
            # Cache as singleton if registered as singleton
            if self._is_singleton.get(service_type, True):
                self._singletons[service_type] = instance
                logger.debug(f"Created and cached singleton: {service_type.__name__}")
            return instance

        raise KeyError(f"Service not registered: {service_type.__name__}")

    def resolve_transient(self, service_type: type[T]) -> T:
        """Resolve a new instance each time (transient)."""
        if service_type in self._factories:
            return self._factories[service_type]()
        raise KeyError(f"Service not registered: {service_type.__name__}")

    def unregister(self, service_type: type) -> None:
        """Unregister a service."""
        self._services.pop(service_type, None)
        self._factories.pop(service_type, None)
        self._singletons.pop(service_type, None)
        self._is_singleton.pop(service_type, None)

    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._is_singleton.clear()

    def is_registered(self, service_type: type) -> bool:
        """Check if a service is registered."""
        return service_type in self._factories or service_type in self._singletons


# Global container instance
_container: DIContainer | None = None


def get_container() -> DIContainer:
    """Get the global DI container."""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def configure_container() -> DIContainer:
    """Configure the global container with core services."""
    container = get_container()

    # Register core services (lazy imports to avoid circular dependencies)
    def make_event_bus():
        from event_bus import EventBus

        return EventBus()

    def make_config_service():
        from services import ConfigService

        return ConfigService()

    def make_sound_service():
        from services import SoundService

        return SoundService()

    def make_renderer():
        from renderer import Renderer

        return Renderer()

    from event_bus import EventBus
    from renderer import Renderer
    from services import ConfigService, SoundService

    container.register(EventBus, make_event_bus)
    container.register(ConfigService, make_config_service)
    container.register(SoundService, make_sound_service)
    container.register(Renderer, make_renderer)

    return container