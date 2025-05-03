#!/usr/bin/env python3

# Copyright 2024 The Kapitan Authors
# SPDX-FileCopyrightText: 2024 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Templating system for Kapitan.

This module provides a flexible and extensible system for handling different templating tools
like Helm, Kustomize, and others. It includes a base class for templating tools and a registry
for managing them.
"""

import abc
import logging
from typing import Dict, Type, Optional

from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import CompileInputTypeConfig

logger = logging.getLogger(__name__)

class TemplatingTool(InputType):
    """Abstract base class for templating tools.

    This class provides a common interface and base functionality for all templating tools
    in Kapitan. It extends the base InputType class and adds templating-specific features.

    To create a new templating tool:
    1. Create a class that inherits from TemplatingTool
    2. Implement the render() method
    3. Optionally override compile_file() if you need custom output processing
    4. Register your tool with TemplatingToolRegistry

    Example:
        class MyTool(TemplatingTool):
            def render(self, config, input_path, output_path):
                # Implement your tool's rendering logic
                pass

        # Register the tool
        TemplatingToolRegistry.register(MyTool)
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, compile_path: str, search_paths: list, ref_controller, target_name: str, args):
        """Initialize a templating tool.

        Args:
            compile_path: Base path for compiled output
            search_paths: List of paths to search for input files
            ref_controller: Reference controller for handling refs
            target_name: Name of the target being compiled
            args: Additional arguments passed to the tool
        """
        super().__init__(compile_path, search_paths, ref_controller, target_name, args)
        self.tool_name = self.__class__.__name__.lower()

    @abc.abstractmethod
    def render(self, config: CompileInputTypeConfig, input_path: str, output_path: str) -> str:
        """Render templates using the specific tool.

        This is the main method that each templating tool must implement.
        It should handle the actual rendering of templates using the tool's specific logic.

        Args:
            config: Configuration object containing tool-specific settings
            input_path: Path to the input files
            output_path: Path where rendered output should be written

        Returns:
            str: Path to the rendered output

        Raises:
            NotImplementedError: If not implemented by subclass
            ToolSpecificError: If rendering fails (subclass should define specific error)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement render() method"
        )

    def compile_file(self, config: CompileInputTypeConfig, input_path: str, compile_path: str) -> None:
        """Compile a single input file.

        This is the default implementation that uses the tool-specific render() method.
        It can be overridden by specific tools if they need custom output processing.

        Args:
            config: Configuration object containing tool-specific settings
            input_path: Path to the input file
            compile_path: Path to the output directory

        Raises:
            CompileError: If compilation fails
        """
        try:
            output_path = self.render(config, input_path, compile_path)
            # Handle the rendered output
            with open(output_path, 'r') as f:
                content = f.read()
            self.to_file(config, output_path, content)
        except Exception as e:
            logger.error(f"Error rendering {self.tool_name} templates: {str(e)}")
            raise

class TemplatingToolRegistry:
    """Registry for managing templating tools.

    This class provides a central place to register and access different templating tools.
    It uses a singleton pattern to maintain a single registry across the application.

    Example:
        # Register a tool
        TemplatingToolRegistry.register(MyTool)

        # Get a tool
        tool_class = TemplatingToolRegistry.get_tool('mytool')

        # List all tools
        tools = TemplatingToolRegistry.list_tools()
    """

    _tools: Dict[str, Type[TemplatingTool]] = {}
    _instance: Optional['TemplatingToolRegistry'] = None

    def __new__(cls):
        """Ensure only one instance of the registry exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, tool_class: Type[TemplatingTool]) -> None:
        """Register a new templating tool.

        Args:
            tool_class: The templating tool class to register

        Raises:
            ValueError: If tool_class is not a subclass of TemplatingTool
        """
        if not issubclass(tool_class, TemplatingTool):
            raise ValueError(
                f"Tool class {tool_class.__name__} must inherit from TemplatingTool"
            )
        tool_name = tool_class.__name__.lower()
        cls._tools[tool_name] = tool_class
        logger.debug(f"Registered templating tool: {tool_name}")

    @classmethod
    def get_tool(cls, tool_name: str) -> Type[TemplatingTool]:
        """Get a registered templating tool by name.

        Args:
            tool_name: Name of the tool to get (case-insensitive)

        Returns:
            Type[TemplatingTool]: The registered tool class

        Raises:
            KeyError: If the tool is not registered
        """
        tool_name = tool_name.lower()
        if tool_name not in cls._tools:
            raise KeyError(
                f"Templating tool '{tool_name}' not found. "
                f"Available tools: {list(cls._tools.keys())}"
            )
        return cls._tools[tool_name]

    @classmethod
    def list_tools(cls) -> list:
        """List all registered templating tools.

        Returns:
            list: List of registered tool names
        """
        return list(cls._tools.keys()) 