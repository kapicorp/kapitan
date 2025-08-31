"""Skipper - Modern rewrite of Kapitan for generic templated configuration management.

Skipper is a comprehensive configuration management tool that provides:
- Multi-phase compilation with real-time progress tracking
- Pluggable inventory backends with legacy Kapitan compatibility
- Multi-format output (console, plain, JSON) with auto-detection
- Advanced TUI for interactive inventory browsing
- Parallel target compilation with comprehensive error handling

This package provides the core functionality, CLI interface, and integration
with legacy Kapitan systems for seamless migration and compatibility.
"""

__version__ = "2.0.0-dev"
__author__ = "Ricardo Amaro"
__email__ = "ramaro@kapicorp.com"

from skipper.core.exceptions import KapitanError

__all__ = ["KapitanError", "__version__"]
