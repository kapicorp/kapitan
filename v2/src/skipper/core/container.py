"""Lightweight dependency injection system for Skipper.

Provides a simple container for managing application dependencies
with support for singletons, factories, and service registration.
Includes convenient decorators for dependency injection.
"""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from rich.console import Console

from .config import KapitanConfig, get_config
from .formatters import OutputFormatter, create_formatter

T = TypeVar('T')
logger = logging.getLogger(__name__)


class Container:
    """Lightweight dependency injection container for service management.
    
    Supports three types of service registration:
    - Singletons: Shared instances across the application
    - Factories: Functions that create instances on demand
    - Services: Direct instance registration
    
    Attributes:
        _services: Direct service instance storage.
        _factories: Factory function storage.
        _singletons: Singleton instance cache.
    """

    def __init__(self):
        """Initialize empty container with service storage."""
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._singletons: dict[str, Any] = {}

    def register_singleton(self, service_type: str | type, instance: Any) -> None:
        """Register a singleton instance for shared use.
        
        Args:
            service_type: Service identifier (string or type).
            instance: Service instance to register.
        """
        key = self._get_key(service_type)
        self._singletons[key] = instance
        logger.debug(f"Registered singleton: {key}")

    def register_factory(self, service_type: str | type, factory: Callable) -> None:
        """Register a factory function for lazy service creation.
        
        Args:
            service_type: Service identifier (string or type).
            factory: Function that creates service instances.
        """
        key = self._get_key(service_type)
        self._factories[key] = factory
        logger.debug(f"Registered factory: {key}")

    def register_service(self, service_type: str | type, instance: Any) -> None:
        """Register a direct service instance.
        
        Args:
            service_type: Service identifier (string or type).
            instance: Service instance to register.
        """
        key = self._get_key(service_type)
        self._services[key] = instance
        logger.debug(f"Registered service: {key}")

    def get(self, service_type: str | type, default: Any = None) -> Any:
        """Retrieve service instance with precedence: singleton > factory > service.
        
        Args:
            service_type: Service identifier to retrieve.
            default: Default value if service not found.
            
        Returns:
            Service instance.
            
        Raises:
            KeyError: If service not found and no default provided.
        """
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
        """Convert service type to string key for storage.
        
        Args:
            service_type: Service identifier.
            
        Returns:
            String key for internal storage.
        """
        if isinstance(service_type, str):
            return service_type
        return service_type.__name__


# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """Get global container instance, initializing if necessary.
    
    Returns:
        Global Container instance with default services configured.
    """
    global _container
    if _container is None:
        _container = Container()
        _setup_default_services(_container)
    return _container


def _setup_default_services(container: Container) -> None:
    """Configure container with default application services.
    
    Registers standard services like configuration, console, and formatters
    as factories for lazy initialization.
    
    Args:
        container: Container instance to configure.
    """

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
    """Convenience function to get configuration from global container.
    
    Returns:
        Application configuration instance.
    """
    return get_container().get('config')


def get_console_service() -> Console:
    """Convenience function to get console from global container.
    
    Returns:
        Rich console instance.
    """
    return get_container().get('console')


def get_formatter_service() -> OutputFormatter:
    """Convenience function to get formatter from global container.
    
    Returns:
        Output formatter instance.
    """
    return get_container().get('formatter')


def inject(service_type: str | type) -> Callable:
    """Decorator for automatic dependency injection into function parameters.
    
    Args:
        service_type: Type of service to inject.
        
    Returns:
        Decorator that injects the specified service.
    """
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
    """Convert service type to string key (static version).
    
    Args:
        service_type: Service identifier.
        
    Returns:
        String key for service lookup.
    """
    if isinstance(service_type, str):
        return service_type
    return service_type.__name__.lower()


# Decorator for dependency injection
def with_config(func: Callable) -> Callable:
    """Decorator to inject configuration service into function.
    
    Args:
        func: Function to wrap with configuration injection.
        
    Returns:
        Wrapped function with configuration parameter.
    """
    return inject('config')(func)


def with_console(func: Callable) -> Callable:
    """Decorator to inject console service into function.
    
    Args:
        func: Function to wrap with console injection.
        
    Returns:
        Wrapped function with console parameter.
    """
    return inject('console')(func)


def with_formatter(func: Callable) -> Callable:
    """Decorator to inject formatter service into function.
    
    Args:
        func: Function to wrap with formatter injection.
        
    Returns:
        Wrapped function with formatter parameter.
    """
    return inject('formatter')(func)
