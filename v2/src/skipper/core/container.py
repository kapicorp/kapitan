"""Dependency injection container for Skipper."""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from rich.console import Console

from .config import KapitanConfig, get_config
from .formatters import OutputFormatter, create_formatter

T = TypeVar('T')
logger = logging.getLogger(__name__)


class Container:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._singletons: dict[str, Any] = {}

    def register_singleton(self, service_type: str | type, instance: Any) -> None:
        """Register a singleton instance."""
        key = self._get_key(service_type)
        self._singletons[key] = instance
        logger.debug(f"Registered singleton: {key}")

    def register_factory(self, service_type: str | type, factory: Callable) -> None:
        """Register a factory function."""
        key = self._get_key(service_type)
        self._factories[key] = factory
        logger.debug(f"Registered factory: {key}")

    def register_service(self, service_type: str | type, instance: Any) -> None:
        """Register a service instance."""
        key = self._get_key(service_type)
        self._services[key] = instance
        logger.debug(f"Registered service: {key}")

    def get(self, service_type: str | type, default: Any = None) -> Any:
        """Get a service instance."""
        key = self._get_key(service_type)

        # Check singletons first
        if key in self._singletons:
            return self._singletons[key]

        # Check factories
        if key in self._factories:
            instance = self._factories[key]()
            # Cache as singleton for future use
            self._singletons[key] = instance
            return instance

        # Check services
        if key in self._services:
            return self._services[key]

        # Return default if provided
        if default is not None:
            return default

        raise KeyError(f"Service not found: {key}")

    def _get_key(self, service_type: str | type) -> str:
        """Get string key for service type."""
        if isinstance(service_type, str):
            return service_type
        return service_type.__name__


# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """Get the global dependency injection container."""
    global _container
    if _container is None:
        _container = Container()
        _setup_default_services(_container)
    return _container


def _setup_default_services(container: Container) -> None:
    """Setup default services in the container."""

    # Register configuration as a factory (lazy loading)
    container.register_factory('config', get_config)
    container.register_factory(KapitanConfig, get_config)

    # Register console factory
    def create_console() -> Console:
        return Console()

    container.register_factory('console', create_console)
    container.register_factory(Console, create_console)

    # Register formatter factory
    def create_default_formatter() -> OutputFormatter:
        config = container.get('config')
        console = container.get('console')
        return create_formatter(config, console)

    container.register_factory('formatter', create_default_formatter)
    container.register_factory(OutputFormatter, create_default_formatter)


# Convenience functions
def get_config_service() -> KapitanConfig:
    """Get configuration service from container."""
    return get_container().get('config')


def get_console_service() -> Console:
    """Get console service from container."""
    return get_container().get('console')


def get_formatter_service() -> OutputFormatter:
    """Get formatter service from container."""
    return get_container().get('formatter')


def inject(service_type: str | type) -> Callable:
    """Decorator to inject dependencies into function parameters."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Check if the service is already provided in kwargs
            key = _get_key_static(service_type)
            if key not in kwargs:
                container = get_container()
                kwargs[key] = container.get(service_type)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _get_key_static(service_type: str | type) -> str:
    """Static version of _get_key for use outside container."""
    if isinstance(service_type, str):
        return service_type
    return service_type.__name__.lower()


# Decorator for dependency injection
def with_config(func: Callable) -> Callable:
    """Inject configuration into function."""
    return inject('config')(func)


def with_console(func: Callable) -> Callable:
    """Inject console into function."""
    return inject('console')(func)


def with_formatter(func: Callable) -> Callable:
    """Inject formatter into function."""
    return inject('formatter')(func)
